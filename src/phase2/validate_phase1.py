"""Phase 1 output validation gate for Phase 2 pipeline (D-17)."""

import pandas as pd
import numpy as np
from pathlib import Path


REQUIRED_COLUMNS = [
    'tic_id', 'sector', 'tess_mag', 'ra', 'dec', 'candidate_num',
    'tls_period', 'tls_t0', 'tls_sde', 'tls_snr', 'tls_cdpp',
    'tls_depth', 'tls_duration', 'n_valid_cadences', 'preprocessed_path',
]

REQUIRED_NPZ_KEYS = ['time', 'flux', 'flux_raw', 'flux_err', 'quality_mask', 'sector', 'tic_id']


def validate_phase1_outputs(catalogue_path: str = 'data/catalogue/master.parquet') -> None:
    """Validate Phase 1 output files before Phase 2 processing.

    Checks that the master Parquet catalogue exists, has the required columns,
    has at least one SDE≥5 candidate, and that referenced .npz files are
    accessible with the expected keys.

    Args:
        catalogue_path: Path to the master Parquet catalogue.

    Raises:
        FileNotFoundError: If the catalogue file does not exist.
        ValueError: If any validation checks fail (all errors collected and
                    reported together).
    """
    cat_path = Path(catalogue_path)
    if not cat_path.exists():
        raise FileNotFoundError(
            f'Phase 1 catalogue not found: {catalogue_path}\n'
            f'Run Phase 1 pipeline before starting Phase 2.'
        )

    errors = []

    # Load catalogue
    try:
        df = pd.read_parquet(catalogue_path)
    except Exception as exc:
        raise ValueError(f'Cannot read Parquet catalogue {catalogue_path}: {exc}') from exc

    # Check required columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        errors.append(f'Missing required columns: {missing_cols}')

    # Check at least one SDE≥5 candidate
    if 'tls_sde' in df.columns:
        sde5_count = int((df['tls_sde'] >= 5).sum())
        if sde5_count == 0:
            errors.append('No candidates with SDE≥5 found in catalogue.')
    else:
        sde5_count = 0  # Column missing — already flagged above

    # Check all preprocessed_path files exist
    if 'preprocessed_path' in df.columns:
        missing_files = [
            str(p) for p in df['preprocessed_path'].dropna().unique()
            if not Path(str(p)).exists()
        ]
        if missing_files:
            sample = missing_files[:5]
            errors.append(
                f'{len(missing_files)} preprocessed .npz files are missing. '
                f'Sample: {sample}'
            )

        # Sample up to 10 .npz files and check required keys
        sample_paths = df['preprocessed_path'].dropna().unique()
        sample_size = min(10, len(sample_paths))
        npz_errors = []
        for path in sample_paths[:sample_size]:
            try:
                with np.load(str(path)) as npz:
                    missing_keys = [k for k in REQUIRED_NPZ_KEYS if k not in npz]
                    if missing_keys:
                        npz_errors.append(f'{path}: missing keys {missing_keys}')
            except Exception as exc:
                npz_errors.append(f'{path}: cannot load ({exc})')
        if npz_errors:
            errors.append(
                f'NPZ key validation failed for {len(npz_errors)}/{sample_size} sampled files:\n  '
                + '\n  '.join(npz_errors)
            )

    if errors:
        bullet_list = '\n'.join(f'  • {e}' for e in errors)
        raise ValueError(f'Phase 1 output validation failed:\n{bullet_list}')

    print(f'✓ Phase 1 validated: {len(df)} rows, {sde5_count} candidates SDE≥5')
