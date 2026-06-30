"""Extract 8+ engineered features per SDE>=5 candidate."""

import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm

try:
    import cupy as cp
    xp = cp
except ImportError:
    xp = np


FEATURE_COLUMNS = [
    'odd_even_depth_diff',
    'secondary_eclipse_depth',
    'centroid_shift_sigma',
    'v_shape_metric',
    'crowdsap',
    'duration_period_ratio',
    'tls_sde',
    'tls_snr',
]


class FeatureExtractor:
    """Extract 8 engineered features per candidate. Appends to master Parquet.

    Features computed:
        - odd_even_depth_diff: Odd/even transit depth difference in sigma (EB discriminator)
        - secondary_eclipse_depth: Secondary eclipse depth at phase 0.5 (EB signature)
        - centroid_shift_sigma: Flux-weighted centroid shift (set to 0.0; updated by CentroidAnalyzer)
        - v_shape_metric: 1.0=V-shaped (grazing EB), 0.0=U-shaped (planet transit)
        - crowdsap: Crowding correction factor from TICv8 (contamination gate)
        - duration_period_ratio: Transit duration / period ratio
        - tls_sde: Signal Detection Efficiency from Phase 1 (already in catalogue)
        - tls_snr: Signal-to-Noise Ratio from Phase 1 (already in catalogue)

    Args:
        catalogue_path: Path to master.parquet.
        preprocessed_dir: Directory containing preprocessed .npz files.
        folded_dir: Directory containing phase-folded .npz files.
    """

    def __init__(self, catalogue_path: str, preprocessed_dir: str, folded_dir: str):
        self.catalogue_path = catalogue_path
        self.preprocessed_dir = Path(preprocessed_dir)
        self.folded_dir = Path(folded_dir)

    def run_all(self) -> None:
        """Extract features for all SDE>=5 candidates."""
        df = pd.read_parquet(self.catalogue_path)
        sde5 = df[df['tls_sde'] >= 5].copy()
        errors = []

        for idx in tqdm(sde5.index, desc='Extracting features'):
            row = sde5.loc[idx]
            try:
                features = self._extract_single(row)
                for col, val in features.items():
                    df.loc[idx, col] = val
            except Exception as e:
                errors.append({'tic_id': row['tic_id'], 'error': str(e)})

        df.to_parquet(self.catalogue_path)
        if errors:
            print(f'⚠ {len(errors)}/{len(sde5)} candidates failed feature extraction.')
        else:
            print(f'✓ Feature extraction complete: {len(sde5)} candidates processed.')

    def _extract_single(self, row: pd.Series) -> dict:
        """Extract features for one candidate.

        Args:
            row: Parquet row for one candidate.

        Returns:
            Dict mapping feature name → computed value.
        """
        data = np.load(row['preprocessed_path'])
        time, flux = data['time'], data['flux']

        folded_path = row.get('folded_path')
        if folded_path and Path(str(folded_path)).exists():
            folded = np.load(str(folded_path))
            local_view = folded['local']
            global_view = folded['global']
        else:
            local_view = np.zeros(201)
            global_view = np.zeros(2001)

        period = row['tls_period']
        t0 = row['tls_t0']
        duration = row['tls_duration']

        return {
            'odd_even_depth_diff': self._compute_odd_even_depth(
                time, flux, period, t0, duration
            ),
            'secondary_eclipse_depth': self._compute_secondary_eclipse(
                global_view
            ),
            'v_shape_metric': self._compute_v_shape(local_view),
            'crowdsap': row.get('crowdsap', 1.0),
            'duration_period_ratio': duration / period if period > 0 else 0.0,
            # centroid_shift_sigma set to 0.0 here; updated by CentroidAnalyzer (Plan 03)
            'centroid_shift_sigma': 0.0,
        }

    @staticmethod
    def _compute_odd_even_depth(time, flux, period, t0, duration):
        """Odd/even transit depth difference in sigma.

        A large value (>3σ) indicates the signal is likely an eclipsing binary
        where odd and even transits have different depths (secondary eclipse).
        """
        phase = ((time - t0) % period) / period
        transit_half_width = (duration / period) / 2.0
        transit_mask = (phase < transit_half_width) | (phase > (1.0 - transit_half_width))
        epoch_num = np.round((time - t0) / period).astype(int)
        odd_mask = transit_mask & (epoch_num % 2 == 1)
        even_mask = transit_mask & (epoch_num % 2 == 0)

        if odd_mask.sum() < 3 or even_mask.sum() < 3:
            return 0.0

        depth_odd = 1.0 - np.median(flux[odd_mask])
        depth_even = 1.0 - np.median(flux[even_mask])
        err_odd = np.std(flux[odd_mask]) / np.sqrt(odd_mask.sum())
        err_even = np.std(flux[even_mask]) / np.sqrt(even_mask.sum())
        combined_err = np.sqrt(err_odd**2 + err_even**2)

        if combined_err == 0:
            return 0.0
        return float(np.abs(depth_odd - depth_even) / combined_err)

    @staticmethod
    def _compute_secondary_eclipse(global_view):
        """Secondary eclipse depth at phase 0.5 from global view.

        A non-zero secondary eclipse is a strong indicator of an eclipsing
        binary where the companion star is also eclipsed at phase 0.5.
        """
        n = len(global_view)
        # Secondary eclipse is at phase 0.5, which maps to edges of [-0.5, 0.5]
        # In the 2001-point global view: phase ±0.5 = indices 0 and 2000
        # Use window around edges (first/last 5% of array)
        edge_width = max(1, n // 20)  # 100 points
        sec_region = np.concatenate([global_view[:edge_width], global_view[-edge_width:]])
        # Out-of-transit reference: middle 20% excluding transit
        oot_start = int(n * 0.25)
        oot_end = int(n * 0.45)
        oot_region = global_view[oot_start:oot_end]
        sec_depth = np.median(oot_region) - np.median(sec_region)
        return float(max(sec_depth, 0.0))

    @staticmethod
    def _compute_v_shape(local_view):
        """V-shape metric: 1.0 = V-shaped (grazing EB), 0.0 = U-shaped (planet).

        Computed as: 1 - (flat_bottom_duration / total_transit_duration).
        A flat-bottomed transit (planet) gives a low value; a V-shaped transit
        (grazing EB) gives a value close to 1.
        """
        depth = 1.0 - np.min(local_view)
        if depth < 1e-5:
            return 0.0

        half_depth_level = 1.0 - depth / 2.0

        # Find points below half-depth (transit region)
        below_half = local_view < half_depth_level
        if not below_half.any():
            return 1.0

        transit_indices = np.where(below_half)[0]
        total_duration = transit_indices[-1] - transit_indices[0] + 1

        if total_duration == 0:
            return 1.0

        # Flat bottom: points within 10% of minimum
        flat_threshold = np.min(local_view) + 0.1 * depth
        flat_duration = np.sum(local_view < flat_threshold)

        return float(1.0 - (flat_duration / total_duration))
