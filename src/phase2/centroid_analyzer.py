"""TPF-based centroid shift analysis for blend detection (FEAT-02).

Downloads Target Pixel Files for top SDE>=7 candidates and computes
flux-weighted centroid shift in-transit vs out-of-transit. Shift > 3σ
flags the candidate as a background blend.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import lightkurve as lk


CENTROID_SHIFT_THRESHOLD_SIGMA = 3.0
CROWDSAP_BLOCK_THRESHOLD = 0.5
CROWDSAP_INVESTIGATE_THRESHOLD = 0.9


class CentroidAnalyzer:
    """Compute centroid shift from TPF data for top SDE>=7 candidates.

    Downloads TPFs via lightkurve/TESScut, computes flux-weighted centroid
    in-transit vs out-of-transit, and updates centroid_shift_sigma in Parquet.

    The centroid shift is computed as the displacement (in pixels) between the
    flux-weighted centroid position during transit vs out-of-transit, divided
    by the OOT centroid scatter (sigma). A shift >3σ indicates the transit is
    occurring on a background star rather than the target — flagging a blend.

    Args:
        catalogue_path: Path to master.parquet.
        tpf_cache_dir: Directory to cache downloaded TPF FITS files.
        top_n: Number of top SDE>=7 candidates to analyze (default 200).
    """

    def __init__(self, catalogue_path: str, tpf_cache_dir: str = 'data/tpf',
                 top_n: int = 200):
        self.catalogue_path = catalogue_path
        self.tpf_cache_dir = Path(tpf_cache_dir)
        self.tpf_cache_dir.mkdir(parents=True, exist_ok=True)
        self.top_n = top_n

    def run_top_n(self) -> None:
        """Run centroid analysis on top N SDE>=7 candidates sorted by SDE."""
        df = pd.read_parquet(self.catalogue_path)

        # Select top N SDE>=7 candidates
        sde7 = df[df['tls_sde'] >= 7].nlargest(self.top_n, 'tls_sde')
        errors = []

        for idx in tqdm(sde7.index, desc='Centroid analysis'):
            row = sde7.loc[idx]
            tic_id = row['tic_id']

            # Skip if already computed (non-zero value)
            if df.loc[idx, 'centroid_shift_sigma'] != 0.0:
                continue

            try:
                shift_sigma = self._analyze_single(
                    tic_id=int(tic_id),
                    sector=int(row['sector']),
                    period=row['tls_period'],
                    t0=row['tls_t0'],
                    duration=row['tls_duration'],
                )
                df.loc[idx, 'centroid_shift_sigma'] = shift_sigma
            except Exception as e:
                errors.append({'tic_id': tic_id, 'error': str(e)})

        df.to_parquet(self.catalogue_path)

        # Summary
        analyzed = len(sde7) - len(errors)
        blends = (df.loc[sde7.index, 'centroid_shift_sigma'] > CENTROID_SHIFT_THRESHOLD_SIGMA).sum()
        print(f'✓ Centroid analysis: {analyzed}/{len(sde7)} analyzed, '
              f'{blends} blend flags (>{CENTROID_SHIFT_THRESHOLD_SIGMA}σ)')
        if errors:
            print(f'⚠ {len(errors)} candidates failed (TPF download or computation).')

    def _analyze_single(self, tic_id: int, sector: int, period: float,
                        t0: float, duration: float) -> float:
        """Compute centroid shift for one candidate.

        Args:
            tic_id: TIC identifier of the target star.
            sector: TESS sector number.
            period: Transit period in days.
            t0: Transit reference epoch in BJD.
            duration: Transit duration in days.

        Returns:
            Centroid shift in units of sigma (shift_pixels / scatter_oot).
            Returns 0.0 if TPF cannot be downloaded or insufficient data.
        """
        tpf = self._download_tpf(tic_id, sector)
        if tpf is None:
            return 0.0

        # Create transit mask from period, t0, duration
        times = tpf.time.value
        phase = ((times - t0) % period) / period
        transit_half_width = (duration / period) / 2.0
        transit_mask = (phase < transit_half_width) | (phase > (1.0 - transit_half_width))

        if transit_mask.sum() < 3 or (~transit_mask).sum() < 10:
            return 0.0

        # Compute flux-weighted centroids
        shift_pixels, shift_sigma = self._compute_centroid_shift(
            tpf.flux.value, transit_mask
        )
        return shift_sigma

    def _download_tpf(self, tic_id: int, sector: int):
        """Download TPF via lightkurve, with caching.

        Args:
            tic_id: TIC identifier.
            sector: TESS sector number.

        Returns:
            lightkurve TargetPixelFile object, or None if download fails.
        """
        cache_path = self.tpf_cache_dir / f'TIC_{tic_id}_s{sector}_tpf.fits'

        if cache_path.exists():
            try:
                return lk.read(str(cache_path))
            except Exception:
                pass

        try:
            search = lk.search_targetpixelfile(
                f'TIC {tic_id}', sector=sector, author='SPOC'
            )
            if len(search) == 0:
                return None
            tpf = search.download()
            # Cache for future runs
            tpf.to_fits(str(cache_path), overwrite=True)
            return tpf
        except Exception:
            return None

    @staticmethod
    def _compute_centroid_shift(flux_cube: np.ndarray,
                                transit_mask: np.ndarray) -> tuple:
        """Compute flux-weighted centroid shift between in-transit and OOT.

        Computes per-frame flux-weighted centroid positions (x, y in pixel
        coordinates), takes medians for in-transit and OOT frames, and
        returns the shift normalized by the OOT centroid scatter.

        Args:
            flux_cube: (n_cadences, n_rows, n_cols) pixel flux array.
            transit_mask: (n_cadences,) boolean — True for in-transit frames.

        Returns:
            (shift_pixels, shift_sigma): absolute shift and significance.
        """
        n_rows, n_cols = flux_cube.shape[1], flux_cube.shape[2]
        ys, xs = np.mgrid[:n_rows, :n_cols]

        def centroid_per_frame(frames):
            """Compute flux-weighted centroid for each frame, return arrays."""
            total = frames.sum(axis=(1, 2))
            # Avoid division by zero
            valid = total > 0
            cx = np.full(len(frames), np.nan)
            cy = np.full(len(frames), np.nan)
            cx[valid] = (frames[valid] * xs).sum(axis=(1, 2)) / total[valid]
            cy[valid] = (frames[valid] * ys).sum(axis=(1, 2)) / total[valid]
            return cx, cy

        # In-transit centroid
        in_frames = flux_cube[transit_mask]
        cx_in, cy_in = centroid_per_frame(in_frames)
        med_cx_in = np.nanmedian(cx_in)
        med_cy_in = np.nanmedian(cy_in)

        # Out-of-transit centroid
        oot_frames = flux_cube[~transit_mask]
        cx_oot, cy_oot = centroid_per_frame(oot_frames)
        med_cx_oot = np.nanmedian(cx_oot)
        med_cy_oot = np.nanmedian(cy_oot)

        # Shift in pixels
        shift_pixels = np.sqrt(
            (med_cx_in - med_cx_oot) ** 2 + (med_cy_in - med_cy_oot) ** 2
        )

        # Sigma: scatter of OOT per-frame centroids
        oot_distances = np.sqrt(
            (cx_oot - med_cx_oot) ** 2 + (cy_oot - med_cy_oot) ** 2
        )
        sigma = np.nanstd(oot_distances)

        if sigma == 0 or np.isnan(sigma):
            return shift_pixels, 0.0

        shift_sigma = shift_pixels / sigma
        return shift_pixels, shift_sigma
