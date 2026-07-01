"""ExoFOP Label Mapper - Cross-match ExoFOP-TESS dispositions to master catalogue.

Maps TFOPWG (TESS Follow-up Observing Program Working Group) dispositions to the
4-class label scheme used for CNN training:
    0 = Planet Candidate (PC)
    1 = Eclipsing Binary (EB)  
    2 = Background Blend
    3 = Stellar Variability

Bugs addressed:
    - Bug #3: Missing 'label' column in master Parquet
    - Bug #15: No ExoFOP → label column mapping script

Usage:
    python scripts/label_mapper.py [--catalogue PATH] [--exofop PATH]
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import pipeline.config as cfg


# TFOPWG Disposition mapping to 4-class labels
# Reference: https://exofop.ipac.caltech.edu/tess/help.php#dispositions
TFOPWG_MAPPING = {
    # Planet Candidates (class 0)
    'KP': 0,       # Known Planet
    'CP': 0,       # Confirmed Planet
    'PC': 0,       # Planet Candidate
    'APC': 0,      # Ambiguous Planet Candidate
    'VPC': 0,      # Validated Planet Candidate
    
    # Eclipsing Binaries (class 1)
    'EB': 1,       # Eclipsing Binary
    'SB': 1,       # Spectroscopic Binary
    
    # Background Blends (class 2)
    'BEB': 2,      # Background Eclipsing Binary (blend)
    'NEB': 2,      # Nearby Eclipsing Binary (blend)
    'BTP': 2,      # Background Transiting Planet (blend)
    
    # Stellar Variability / False Alarms (class 3)
    'V': 3,        # Variable Star
    'IS': 3,       # Instrumental Systematic
    'O': 3,        # Other / Unknown
    'FA': 3,       # False Alarm
    'FP': 3,       # False Positive (generic)
    'SG': 3,       # Star Grazers / contamination
}

# Alternative column names that might contain dispositions
DISPOSITION_COLUMNS = [
    'TFOPWG Disposition',
    'tfopwg_disp',
    'ACWG Disposition',
    'disposition',
    'Disposition',
]

CLASS_NAMES = ['PC', 'EB', 'Blend', 'StellarVar']


def map_disposition_to_label(disp: str) -> int:
    """Map TFOPWG disposition string to 4-class integer label.
    
    Args:
        disp: Disposition string from ExoFOP.
        
    Returns:
        Integer label 0-3, or -1 if unknown/unmappable.
    """
    if pd.isna(disp) or str(disp).strip() == '':
        return -1
    
    disp_upper = str(disp).strip().upper()
    
    # Direct mapping
    if disp_upper in TFOPWG_MAPPING:
        return TFOPWG_MAPPING[disp_upper]
    
    # Fuzzy matching for common variations
    if 'PLANET' in disp_upper or disp_upper.startswith('P'):
        if 'BACKGROUND' in disp_upper:
            return 2  # Background planet = blend
        return 0  # Planet candidate
    
    if 'BINARY' in disp_upper or 'EB' in disp_upper:
        if 'BACKGROUND' in disp_upper or 'NEARBY' in disp_upper:
            return 2  # Background/nearby EB = blend
        return 1  # Eclipsing binary
    
    if 'BLEND' in disp_upper or 'CONTAM' in disp_upper:
        return 2  # Blend
    
    if any(x in disp_upper for x in ['VARIABLE', 'STELLAR', 'FALSE', 'INSTRUMENT']):
        return 3  # Stellar variability / false positive
    
    # Unknown - return -1 (will be excluded from training)
    return -1


def find_disposition_column(df: pd.DataFrame) -> str:
    """Find the disposition column in the dataframe.
    
    Args:
        df: ExoFOP dataframe.
        
    Returns:
        Column name containing dispositions, or None if not found.
    """
    for col in DISPOSITION_COLUMNS:
        if col in df.columns:
            return col
    
    # Try case-insensitive match
    df_cols_lower = {c.lower(): c for c in df.columns}
    for col in DISPOSITION_COLUMNS:
        if col.lower() in df_cols_lower:
            return df_cols_lower[col.lower()]
    
    return None


def load_exofop_toi(exofop_path: str) -> pd.DataFrame:
    """Load ExoFOP TOI table, handling various formats.
    
    Args:
        exofop_path: Path to ExoFOP CSV file.
        
    Returns:
        DataFrame with TIC ID and disposition columns.
    """
    df = pd.read_csv(exofop_path, comment='#')
    
    # Find TIC ID column
    tic_col = None
    for col in ['TIC ID', 'TIC', 'tic_id', 'ticid']:
        if col in df.columns:
            tic_col = col
            break
    
    if tic_col is None:
        raise ValueError(f"Cannot find TIC ID column in {exofop_path}. Columns: {list(df.columns)}")
    
    # Normalize TIC ID column name
    df = df.rename(columns={tic_col: 'tic_id'})
    
    # Convert TIC ID to integer
    df['tic_id'] = pd.to_numeric(df['tic_id'], errors='coerce').astype('Int64')
    df = df.dropna(subset=['tic_id'])
    
    return df


def main(args):
    """Main entry point for label mapping."""
    
    # Load master catalogue
    catalogue_path = Path(args.catalogue)
    if not catalogue_path.exists():
        print(f"Error: Catalogue not found at {catalogue_path}")
        return 1
    
    print(f"Loading catalogue from {catalogue_path}...")
    cat_df = pd.read_parquet(catalogue_path)
    print(f"Loaded {len(cat_df)} entries")
    
    # Check if tic_id column exists
    if 'tic_id' not in cat_df.columns:
        print("Error: 'tic_id' column not found in catalogue")
        return 1
    
    # Load ExoFOP table
    exofop_path = Path(args.exofop)
    if not exofop_path.exists():
        # Try default location
        default_path = Path('data/reference/exofop_toi_dispositions.csv')
        if default_path.exists():
            exofop_path = default_path
        else:
            print(f"Error: ExoFOP file not found at {args.exofop}")
            print("Download it first: python scripts/download_exofop.py")
            return 1
    
    print(f"Loading ExoFOP table from {exofop_path}...")
    exofop_df = load_exofop_toi(str(exofop_path))
    print(f"Loaded {len(exofop_df)} TOI entries")
    
    # Find disposition column
    disp_col = find_disposition_column(exofop_df)
    if disp_col is None:
        print(f"Warning: No disposition column found in ExoFOP table")
        print(f"Available columns: {list(exofop_df.columns)}")
        print("Will check for TOI column to assign default PC label...")
        
        # If no disposition, assume all TOIs are planet candidates
        if 'TOI' in exofop_df.columns or 'toi' in [c.lower() for c in exofop_df.columns]:
            exofop_df['_disposition'] = 'PC'
            disp_col = '_disposition'
        else:
            print("Error: Cannot determine dispositions")
            return 1
    
    print(f"Using disposition column: '{disp_col}'")
    
    # Print disposition distribution
    print("\nExoFOP disposition distribution:")
    disp_counts = exofop_df[disp_col].value_counts(dropna=False)
    for disp, count in disp_counts.head(15).items():
        label = map_disposition_to_label(disp)
        label_name = CLASS_NAMES[label] if label >= 0 else 'EXCLUDED'
        print(f"  {disp}: {count} → {label_name}")
    
    # Map dispositions to labels
    exofop_df['_label'] = exofop_df[disp_col].apply(map_disposition_to_label)
    
    # Create mapping dict: tic_id → label
    # Take the first (highest priority) disposition per TIC
    label_map = exofop_df.groupby('tic_id')['_label'].first().to_dict()
    
    # Apply to catalogue
    initial_labeled = cat_df['label'].notna().sum() if 'label' in cat_df.columns else 0
    
    cat_df['label'] = cat_df['tic_id'].map(label_map)
    
    # Convert to nullable Int64 to handle NaN properly
    cat_df['label'] = cat_df['label'].astype('Int64')
    
    # Report results
    new_labeled = cat_df['label'].notna().sum()
    matched = (cat_df['label'] >= 0).sum() if new_labeled > 0 else 0
    
    print(f"\nLabel mapping results:")
    print(f"  Catalogue entries: {len(cat_df)}")
    print(f"  Previously labeled: {initial_labeled}")
    print(f"  Matched with ExoFOP: {new_labeled}")
    print(f"  Valid labels (0-3): {matched}")
    
    # Filter out invalid labels (-1)
    cat_df.loc[cat_df['label'] == -1, 'label'] = pd.NA
    
    final_labeled = cat_df['label'].notna().sum()
    print(f"  Final labeled count: {final_labeled}")
    
    # Print class distribution
    print("\nClass distribution in catalogue:")
    for i, name in enumerate(CLASS_NAMES):
        count = (cat_df['label'] == i).sum()
        pct = 100 * count / final_labeled if final_labeled > 0 else 0
        print(f"  {name} (class {i}): {count} ({pct:.1f}%)")
    
    # Save updated catalogue
    print(f"\nSaving updated catalogue to {catalogue_path}...")
    cat_df.to_parquet(catalogue_path, index=False)
    
    print(f"✓ Label mapping complete: {final_labeled} entries labeled")
    
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Map ExoFOP-TESS dispositions to 4-class labels in catalogue'
    )
    parser.add_argument('--catalogue', type=str, 
                        default=str(cfg.MASTER_CATALOGUE_PATH),
                        help='Path to master catalogue Parquet')
    parser.add_argument('--exofop', type=str,
                        default='data/reference/exofop_toi_dispositions.csv',
                        help='Path to ExoFOP TOI dispositions CSV')
    args = parser.parse_args()
    
    exit(main(args))
