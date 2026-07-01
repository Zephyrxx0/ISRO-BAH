"""Phase-fold light curves into 2001-global + 201-local views for CNN input."""

import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm

try:
    import cupy as cp
    xp = cp
except ImportError:
    xp = np


class PhaseFolder:
    """Generate phase-folded views per candidate (D-08).

    Reads preprocessed .npz + catalogue rows, produces
    data/folded/TIC_{id}_folded.npz with keys 'global' (2001,) and 'local' (201,).

    Args:
        catalogue_path: Path to master.parquet.
        preprocessed_dir: Directory containing preprocessed .npz files.
        folded_dir: Output directory for phase-folded .npz files.
    """

    GLOBAL_LEN = 2001
    LOCAL_LEN = 201

    def __init__(self, catalogue_path: str, preprocessed_dir: str, folded_dir: str):
        self.catalogue_path = catalogue_path
        self.preprocessed_dir = Path(preprocessed_dir)
        self.folded_dir = Path(folded_dir)
        self.folded_dir.mkdir(parents=True, exist_ok=True)

    def run_all(self) -> None:
        """Phase-fold all SDE>=5 candidates. Skips already-folded (checkpoint)."""
        df = pd.read_parquet(self.catalogue_path)
        sde5 = df[df['tls_sde'] >= 5].copy()
        errors = []
        folded_paths = {}

        for idx in tqdm(sde5.index, desc='Phase-folding'):
            row = sde5.loc[idx]
            tic_id = row['tic_id']
            output_path = self.folded_dir / f'TIC_{tic_id}_folded.npz'

            if output_path.exists():
                folded_paths[idx] = str(output_path)
                continue

            try:
                data = np.load(row['preprocessed_path'])
                time, flux = data['time'], data['flux']
                global_view, local_view = self.fold_single(
                    time, flux, row['tls_period'], row['tls_t0'], row['tls_duration']
                )
                np.savez_compressed(output_path, **{'global': global_view, 'local': local_view})
                folded_paths[idx] = str(output_path)
            except Exception as e:
                errors.append({'tic_id': tic_id, 'error': str(e)})

        # Update catalogue with folded_path column
        df['folded_path'] = None
        for idx, path in folded_paths.items():
            df.loc[idx, 'folded_path'] = path
        df.to_parquet(self.catalogue_path)

        if errors:
            print(f'⚠ {len(errors)}/{len(sde5)} candidates failed phase-folding.')
        else:
            print(f'✓ Phase-folding complete: {len(folded_paths)}/{len(sde5)} candidates folded.')

    def fold_single(self, time: np.ndarray, flux: np.ndarray,
                    period: float, t0: float, duration: float) -> tuple:
        """Fold one light curve into global (2001) + local (201) views.

        Normalization: median=0, min=-1 per AstroNet spec.

        Args:
            time: Array of time values (BJD).
            flux: Normalized, detrended flux array.
            period: Transit period in days.
            t0: Transit reference epoch in BJD.
            duration: Transit duration in days.

        Returns:
            Tuple of (global_view, local_view) as float32 arrays.
        """
        phase = ((time - t0) % period) / period
        phase[phase > 0.5] -= 1.0  # Center transit at phase 0

        # Global view: 2001 bins spanning [-0.5, 0.5]
        global_bins = np.linspace(-0.5, 0.5, self.GLOBAL_LEN + 1)
        global_view = np.zeros(self.GLOBAL_LEN, dtype=np.float32)
        for i in range(self.GLOBAL_LEN):
            mask = (phase >= global_bins[i]) & (phase < global_bins[i + 1])
            global_view[i] = np.median(flux[mask]) if mask.sum() > 0 else 0.0

        # Local view: 201 bins spanning ±2× transit duration in phase
        half_width = min(2.0 * (duration / period), 0.25)
        local_bins = np.linspace(-half_width, half_width, self.LOCAL_LEN + 1)
        local_view = np.zeros(self.LOCAL_LEN, dtype=np.float32)
        for i in range(self.LOCAL_LEN):
            mask = (phase >= local_bins[i]) & (phase < local_bins[i + 1])
            local_view[i] = np.median(flux[mask]) if mask.sum() > 0 else 0.0

        # Normalize: median=0, min=-1
        global_view = self._normalize(global_view)
        local_view = self._normalize(local_view)

        return global_view, local_view

    @staticmethod
    def _normalize(view: np.ndarray) -> np.ndarray:
        """Normalize view: subtract median, scale so min=-1.
        
        Bug #7 Fix: Handle edge cases where:
        - All values are the same (flat view)
        - All values are zero (empty bins)
        - min_val is exactly 0 after median subtraction
        
        Returns view with median=0 and min=-1 when possible,
        or zeros if view has no variance.
        """
        # Handle NaN values first
        view = np.nan_to_num(view, nan=0.0, posinf=0.0, neginf=0.0)
        
        median_val = np.median(view)
        view = view - median_val
        
        min_val = np.min(view)
        
        # Bug #7 Fix: Guard against division by zero
        # Only scale if there's a meaningful dip (transit depth)
        if min_val < -1e-10:  # Has a real negative dip
            view = view / np.abs(min_val)
        # If min_val >= 0 or very small, view stays as median-subtracted
        # This handles flat views, all-zero views, and views with no transit
        
        return view.astype(np.float32)
