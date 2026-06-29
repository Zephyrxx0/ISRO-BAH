import json
import numpy as np
from pathlib import Path
import pipeline.config as cfg

def npz_path(tic_id, sector, kind='raw'):
    """Return Path object for a given TIC ID and sector."""
    # Assuming baseline signature exists from repo context
    ...

def save_lc_npz(tic_id, sector, time, flux, flux_err, quality, meta, kind='raw'):
    """Save lightcurve data to compressed npz file, serializing meta as JSON."""
    path = npz_path(tic_id, sector, kind=kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Serialize the meta dictionary to a JSON string
    meta_json = json.dumps(meta)
    
    np.savez_compressed(
        str(path),
        time=time,
        flux=flux,
        flux_err=flux_err,
        quality=quality,
        meta_json=meta_json
    )
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
