"""Phase 1 output validation gate for Phase 2 pipeline (D-17).

Bug #4 Fix: Reconcile paths between Phase 1 output and Phase 2 input.
Bug #13 Fix: Align column expectations with actual Phase 1 output schema.

The actual Phase 1 pipeline (pipeline/run_pipeline.py) outputs to:
    - outputs/catalogue/master_catalogue.parquet (not data/catalogue/master.parquet)
    - outputs/preprocessed/ (not data/preprocessed/)

This validator checks both possible locations for backwards compatibility.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add project root to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import pipeline.config as cfg
    PHASE1_CATALOGUE_PATH = cfg.MASTER_CATALOGUE_PATH
    PHASE1_PREP_DIR = cfg.PREP_DIR
except ImportError:
    PHASE1_CATALOGUE_PATH = Path('outputs/catalogue/master_catalogue.parquet')
    PHASE1_PREP_DIR = Path('outputs/preprocessed')


# Bug #13 Fix: Updated column names to match actual Phase 1 TLS output
# The TLS search stores columns as: period, sde, snr, etc. (not tls_period, etc.)
REQUIRED_COLUMNS_STRICT = [
    'tic_id', 'sector', 'period', 't0', 'sde', 'snr', 'depth', 'duration',
]

# Extended columns that may exist (with tls_ prefix from some code paths)
REQUIRED_COLUMNS_FLEXIBLE = [
    ('tic_id', 'TIC_ID', 'ticid'),
    ('sector',),
    ('period', 'tls_period'),
    ('t0', 'tls_t0'),
    ('sde', 'tls_sde'),
    ('snr', 'tls_snr'),
    ('depth', 'tls_depth'),
    ('duration', 'tls_duration'),
]

# Optional columns that enhance but aren't required
OPTIONAL_COLUMNS = [
    'candidate_num', 'planet_num', 'tess_mag', 'tmag', 'ra', 'dec',
    'cdpp', 'tls_cdpp', 'n_valid_cadences', 'n_cadences',
    'preprocessed_path', 'crowdsap',
]

# NPZ keys - flexible to handle both Phase 1 output formats
REQUIRED_NPZ_KEYS_ANY = [
    ('time',),
    ('flux',),
    ('flux_err',),
]


def _find_column(df: pd.DataFrame, column_options: tuple) -> str:
    """Find which column name variant exists in the dataframe.
    
    Args:
        df: DataFrame to search.
        column_options: Tuple of possible column names.
        
    Returns:
        The column name that exists, or None if none found.
    """
    for col in column_options:
        if col in df.columns:
            return col
    return None


def _find_catalogue_path(custom_path: str = None) -> Path:
    """Find the Phase 1 catalogue, checking multiple locations.
    
    Bug #4 Fix: Handle both planned and actual path conventions.
    
    Args:
        custom_path: User-specified path (takes precedence if exists).
        
    Returns:
        Path to catalogue file that exists.
        
    Raises:
        FileNotFoundError if no catalogue found.
    """
    search_paths = []
    
    if custom_path:
        search_paths.append(Path(custom_path))
    
    # Check planned path (Phase 2 convention)
    search_paths.append(Path('data/catalogue/master.parquet'))
    
    # Check actual Phase 1 output path
    search_paths.append(PHASE1_CATALOGUE_PATH)
    search_paths.append(Path('outputs/catalogue/master_catalogue.parquet'))
    
    # Check TLS results directly
    search_paths.append(Path('outputs/catalogue/tls_candidates.parquet'))
    
    for path in search_paths:
        if path.exists():
            return path
    
    raise FileNotFoundError(
        f'Phase 1 catalogue not found. Searched:\n'
        + '\n'.join(f'  - {p}' for p in search_paths)
        + '\nRun Phase 1 pipeline before starting Phase 2.'
    )


def validate_phase1_outputs(catalogue_path: str = None) -> None:
    """Validate Phase 1 output files before Phase 2 processing.

    Checks that the master Parquet catalogue exists, has the required columns
    (with flexible naming), has at least one SDE≥5 candidate, and that 
    referenced .npz files are accessible.

    Args:
        catalogue_path: Path to the master Parquet catalogue.
                       If None, searches default locations.

    Raises:
        FileNotFoundError: If the catalogue file does not exist.
        ValueError: If any validation checks fail.
    """
    # Bug #4 Fix: Find catalogue with flexible path resolution
    cat_path = _find_catalogue_path(catalogue_path)
    print(f'Found Phase 1 catalogue: {cat_path}')

    errors = []

    # Load catalogue
    try:
        df = pd.read_parquet(cat_path)
    except Exception as exc:
        raise ValueError(f'Cannot read Parquet catalogue {cat_path}: {exc}') from exc

    # Bug #13 Fix: Check required columns with flexible naming
    column_mapping = {}
    missing_cols = []
    
    for col_options in REQUIRED_COLUMNS_FLEXIBLE:
        found = _find_column(df, col_options)
        if found:
            column_mapping[col_options[0]] = found
        else:
            missing_cols.append(col_options[0])
    
    if missing_cols:
        errors.append(
            f'Missing required columns: {missing_cols}\n'
            f'Available columns: {list(df.columns)}'
        )

    # Check at least one SDE≥5 candidate
    sde_col = column_mapping.get('sde')
    if sde_col and sde_col in df.columns:
        sde5_count = int((df[sde_col] >= 5).sum())
        if sde5_count == 0:
            errors.append('No candidates with SDE≥5 found in catalogue.')
    else:
        sde5_count = 0

    # Check preprocessed files if path column exists
    path_col = _find_column(df, ('preprocessed_path', 'prep_path', 'lc_path'))
    if path_col:
        missing_files = [
            str(p) for p in df[path_col].dropna().unique()
            if not Path(str(p)).exists()
        ]
        if missing_files and len(missing_files) > len(df) * 0.5:
            # Only error if majority of files missing
            sample = missing_files[:5]
            errors.append(
                f'{len(missing_files)} preprocessed .npz files are missing. '
                f'Sample: {sample}'
            )

    # Sample NPZ files and check keys (flexible)
    if path_col and path_col in df.columns:
        sample_paths = df[path_col].dropna().unique()
        sample_size = min(10, len(sample_paths))
        npz_errors = []
        
        for path in sample_paths[:sample_size]:
            try:
                if not Path(str(path)).exists():
                    continue
                with np.load(str(path), allow_pickle=False) as npz:
                    npz_keys = set(npz.files)
                    missing_keys = []
                    for key_options in REQUIRED_NPZ_KEYS_ANY:
                        if not any(k in npz_keys for k in key_options):
                            missing_keys.append(key_options[0])
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
