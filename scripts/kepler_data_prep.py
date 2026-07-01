"""Kepler DR24 Data Preparation - Phase-fold light curves and map labels for CNN pre-training.

This script transforms raw Kepler DR24 light curves into the training format expected by
train_kepler.py. It produces data/kepler/kepler_dr24_folded.npz with:
    - global_views: (N, 2001) float32 array of phase-folded global views
    - local_views: (N, 201) float32 array of phase-folded local views  
    - labels: (N,) int32 array of 4-class labels (0=PC, 1=EB, 2=Blend, 3=StellarVar)
    - kic_ids: (N,) int64 array of KIC IDs for data leak prevention in splits

Bugs addressed:
    - Bug #1: Missing kepler_data_prep.py script
    - Bug #8: Kepler DR24 4-class label mapping (AFP, NTP, etc.)
    - Bug #14: Phase-folding with proper normalization

Usage:
    python scripts/kepler_data_prep.py [--limit N] [--workers W]
"""

import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pipeline.config as cfg


# 4-class label mapping from Kepler DR24 av_training_set
# Based on Shallue & Vanderburg 2018 AstroNet labels
LABEL_MAPPING = {
    # Planet Candidate (class 0)
    'PC': 0,       # Confirmed planet
    'KP': 0,       # Known planet (legacy label)
    
    # Eclipsing Binary (class 1)
    'EB': 1,       # Eclipsing binary
    'AFP': 1,      # Astrophysical False Positive - primarily EBs
    
    # Background Blend (class 2) - Note: DR24 doesn't explicitly separate blends
    # We'll map some AFPs here based on centroid analysis if available
    # For now, map known blend indicators to class 2
    'BEB': 2,      # Background eclipsing binary (blend)
    
    # Stellar Variability (class 3)
    'NTP': 3,      # Non-Transiting Phenomenon (stellar activity)
    'V': 3,        # Variable star
    'UNK': 3,      # Unknown - treat as stellar noise
    'IS': 3,       # Instrumental - actually filtered in preprocessing
}

# Classes that are valid for training
VALID_LABELS = {0, 1, 2, 3}
CLASS_NAMES = ['PC', 'EB', 'Blend', 'StellarVar']


def map_label(av_training_set: str) -> int:
    """Map Kepler DR24 av_training_set to 4-class integer label.
    
    Args:
        av_training_set: Original label string from DR24 catalog.
        
    Returns:
        Integer label 0-3, or -1 if label should be excluded.
    """
    if pd.isna(av_training_set) or av_training_set == '':
        return -1  # Exclude unlabeled
    
    label_upper = str(av_training_set).strip().upper()
    
    # Direct mapping
    if label_upper in LABEL_MAPPING:
        return LABEL_MAPPING[label_upper]
    
    # Handle common variations
    if 'PLANET' in label_upper or label_upper == 'CP':
        return 0  # PC
    if 'BINARY' in label_upper or 'EB' in label_upper:
        return 1  # EB
    if 'BLEND' in label_upper or 'BEB' in label_upper:
        return 2  # Blend
    if 'VARIABLE' in label_upper or 'STELLAR' in label_upper:
        return 3  # StellarVar
        
    # Default: treat unknown as stellar variability
    print(f"Warning: Unknown label '{av_training_set}' mapped to StellarVar")
    return 3


def phase_fold_kepler(time: np.ndarray, flux: np.ndarray, 
                      period: float, t0: float, duration: float,
                      global_len: int = 2001, local_len: int = 201) -> tuple:
    """Phase-fold a Kepler light curve into global + local views.
    
    Uses the same normalization as TESS pipeline (median=0, min=-1 per AstroNet spec).
    
    Args:
        time: BJD time array.
        flux: Normalized flux array (median ~ 1).
        period: Transit period in days.
        t0: Transit epoch (BJD).
        duration: Transit duration in days.
        global_len: Number of bins for global view (default 2001).
        local_len: Number of bins for local view (default 201).
        
    Returns:
        (global_view, local_view) as float32 arrays.
    """
    # Compute phase centered at 0
    phase = ((time - t0) % period) / period
    phase[phase > 0.5] -= 1.0
    
    # Global view: 2001 bins spanning [-0.5, 0.5]
    global_bins = np.linspace(-0.5, 0.5, global_len + 1)
    global_view = np.zeros(global_len, dtype=np.float32)
    for i in range(global_len):
        mask = (phase >= global_bins[i]) & (phase < global_bins[i + 1])
        if mask.sum() > 0:
            global_view[i] = np.nanmedian(flux[mask])
    
    # Local view: 201 bins spanning ±2× duration
    half_width = min(2.0 * (duration / period), 0.25)
    local_bins = np.linspace(-half_width, half_width, local_len + 1)
    local_view = np.zeros(local_len, dtype=np.float32)
    for i in range(local_len):
        mask = (phase >= local_bins[i]) & (phase < local_bins[i + 1])
        if mask.sum() > 0:
            local_view[i] = np.nanmedian(flux[mask])
    
    # Normalize: median=0, then scale so min=-1
    # Bug #12 fix: Handle edge case where all values are the same
    global_view = _safe_normalize(global_view)
    local_view = _safe_normalize(local_view)
    
    return global_view, local_view


def _safe_normalize(view: np.ndarray) -> np.ndarray:
    """Normalize view with protection against div-by-zero (Bug #12 fix).
    
    Normalization: subtract median, then scale so min=-1.
    If all values are identical or view is all zeros, returns zeros.
    """
    # Handle NaN values
    view = np.nan_to_num(view, nan=0.0)
    
    med = np.median(view)
    view = view - med
    
    min_val = np.min(view)
    
    # Guard against division by zero
    if min_val < -1e-10:  # Has a real dip
        view = view / np.abs(min_val)
    elif min_val > 1e-10:  # All positive after median subtraction (weird case)
        view = view / np.abs(min_val) * -1  # Flip sign
    # else: min_val ≈ 0, leave view as median-subtracted
    
    return view.astype(np.float32)


def process_single_tce(args) -> dict:
    """Process a single TCE entry. Returns dict with views and metadata or None."""
    kic_id, row, kepler_lc_dir = args
    
    try:
        # Load light curve
        lc_path = kepler_lc_dir / f"{kic_id}_kepler.npz"
        if not lc_path.exists():
            return None
            
        with np.load(str(lc_path), allow_pickle=True) as data:
            time = data['time']
            flux = data['flux']
        
        # Basic quality filter
        valid = np.isfinite(time) & np.isfinite(flux)
        time = time[valid]
        flux = flux[valid]
        
        if len(time) < 100:
            return None
        
        # Normalize flux to median=1
        med_flux = np.nanmedian(flux)
        if med_flux <= 0:
            return None
        flux = flux / med_flux
        
        # Extract TCE parameters
        period = float(row['tce_period'])
        t0 = float(row['tce_time0bk'])
        duration = float(row['tce_duration']) / 24.0  # Convert hours to days
        
        if period <= 0 or duration <= 0 or np.isnan(period) or np.isnan(t0):
            return None
        
        # Phase-fold
        global_view, local_view = phase_fold_kepler(time, flux, period, t0, duration)
        
        # Map label
        label = map_label(row.get('av_training_set', ''))
        
        return {
            'kic_id': int(kic_id),
            'global_view': global_view,
            'local_view': local_view,
            'label': label,
            'period': period,
            'depth': float(row.get('tce_depth', 0)),
        }
        
    except Exception as e:
        return None


def main(args):
    """Main entry point for Kepler data preparation."""
    
    # Setup paths
    kepler_lc_dir = cfg.OUTPUTS_DIR / 'kepler'
    output_dir = Path('data/kepler')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'kepler_dr24_folded.npz'
    
    # Load TCE catalog
    tce_path = cfg.KEPLER_TCE_PATH
    if not tce_path.exists():
        print(f"Error: TCE catalog not found at {tce_path}")
        print("Run 'python -c \"from pipeline.ingest.download_kepler import download_kepler_tce_catalog; download_kepler_tce_catalog()\"' first.")
        return 1
    
    print(f"Loading Kepler DR24 TCE catalog from {tce_path}...")
    tce_df = pd.read_csv(tce_path)
    print(f"Loaded {len(tce_df)} TCE entries")
    
    # Check for required columns
    required_cols = ['kepid', 'tce_period', 'tce_time0bk', 'tce_duration']
    missing = [c for c in required_cols if c not in tce_df.columns]
    if missing:
        print(f"Error: Missing required columns in TCE catalog: {missing}")
        return 1
    
    # Check available light curves
    available_kics = set()
    if kepler_lc_dir.exists():
        for f in kepler_lc_dir.glob('*_kepler.npz'):
            try:
                kic_id = int(f.stem.split('_')[0])
                available_kics.add(kic_id)
            except ValueError:
                continue
    
    print(f"Found {len(available_kics)} downloaded Kepler light curves")
    
    # Filter TCE catalog to available KICs
    tce_df = tce_df[tce_df['kepid'].isin(available_kics)]
    print(f"Matched {len(tce_df)} TCE entries with available light curves")
    
    if len(tce_df) == 0:
        print("Error: No matching light curves. Download Kepler data first.")
        return 1
    
    # Apply limit if specified
    if args.limit:
        tce_df = tce_df.head(args.limit)
        print(f"Limited to {len(tce_df)} entries")
    
    # Prepare processing arguments
    process_args = [
        (int(row['kepid']), row, kepler_lc_dir)
        for _, row in tce_df.iterrows()
    ]
    
    # Process with multiprocessing
    results = []
    print(f"Phase-folding {len(process_args)} TCEs with {args.workers} workers...")
    
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(process_single_tce, arg) for arg in process_args]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            result = future.result()
            if result is not None:
                results.append(result)
    
    print(f"Successfully processed {len(results)} TCEs")
    
    # Filter to valid labels only
    results = [r for r in results if r['label'] in VALID_LABELS]
    print(f"After label filtering: {len(results)} TCEs")
    
    if len(results) == 0:
        print("Error: No valid TCEs after processing")
        return 1
    
    # Aggregate into arrays
    global_views = np.stack([r['global_view'] for r in results])
    local_views = np.stack([r['local_view'] for r in results])
    labels = np.array([r['label'] for r in results], dtype=np.int32)
    kic_ids = np.array([r['kic_id'] for r in results], dtype=np.int64)
    
    # Print class distribution
    print("\nClass distribution:")
    for i, name in enumerate(CLASS_NAMES):
        count = (labels == i).sum()
        pct = 100 * count / len(labels)
        print(f"  {name} (class {i}): {count} ({pct:.1f}%)")
    
    # Save to npz
    print(f"\nSaving to {output_path}...")
    np.savez_compressed(
        str(output_path),
        global_views=global_views,
        local_views=local_views,
        labels=labels,
        kic_ids=kic_ids,  # Bug #20: Include KIC IDs for per-star split
    )
    
    print(f"✓ Kepler DR24 preparation complete: {len(results)} samples saved")
    print(f"  Shape: global_views={global_views.shape}, local_views={local_views.shape}")
    
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Prepare Kepler DR24 data for CNN pre-training'
    )
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of TCEs to process (for testing)')
    parser.add_argument('--workers', type=int, default=4,
                        help='Number of parallel workers')
    args = parser.parse_args()
    
    exit(main(args))
