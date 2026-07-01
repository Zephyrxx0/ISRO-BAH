import json
import numpy as np
from pathlib import Path
import pipeline.config as cfg

def npz_path(tic_id, sector, kind='raw'):
    """Return Path object for a given TIC ID and sector."""
    base = cfg.RAW_DIR if kind == 'raw' else cfg.PREP_DIR
    return base / f"tic{tic_id:016d}_s{sector:04d}_{kind}.npz"

def save_lc_npz(tic_id, sector, time, flux, flux_err, quality, meta, kind='raw', **extra_arrays):
    """Save lightcurve data to compressed npz file, serializing meta as JSON.
    
    Bug #10 Fix: Now accepts **extra_arrays for additional data like flux_normalized.
    
    Args:
        tic_id: TIC identifier.
        sector: TESS sector number.
        time: Time array.
        flux: Flux array (detrended for 'preprocessed' kind).
        flux_err: Flux error array.
        quality: Quality flags array (can be None).
        meta: Metadata dictionary.
        kind: File kind ('raw' or 'preprocessed').
        **extra_arrays: Additional named arrays to save (e.g., flux_normalized).
    """
    path = npz_path(tic_id, sector, kind=kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Serialize the meta dictionary to a JSON string
    meta_json = json.dumps(meta)
    
    # Build save dict with required arrays
    save_dict = {
        'time': time,
        'flux': flux,
        'flux_err': flux_err,
        'meta_json': meta_json
    }
    
    # Add quality if provided
    if quality is not None:
        save_dict['quality'] = quality
    
    # Bug #10 Fix: Add any extra arrays (e.g., flux_normalized)
    save_dict.update(extra_arrays)
    
    np.savez_compressed(str(path), **save_dict)
    return path

def load_lc_npz(tic_id, sector, kind='raw'):
    """Load lightcurve data from npz file securely without pickle."""
    path = npz_path(tic_id, sector, kind=kind)
    if not path.exists():
        raise FileNotFoundError(f"No {kind} npz file found for TIC {tic_id} Sector {sector} at {path}")
        
    with np.load(str(path), allow_pickle=False) as data:
        result = {}
        for key in data.files:
            if key == 'meta_json':
                # Reconstruct meta safely via JSON
                result['meta'] = json.loads(str(data[key]))
            else:
                result[key] = data[key]
                
        # Handle backwards-compatibility or structural expectation mapping if needed
        if 'meta_json' in result and 'meta' not in result:
            result['meta'] = result.pop('meta_json')
            
        return result
