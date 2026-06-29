import pandas as pd
import numpy as np
from pathlib import Path
import pipeline.config as cfg

def get_ld_coefficients(tic_id, meta):
    """
    Get limb darkening coefficients (u1, u2) for a star.
    Tries to lookup in the Claret LD table using Teff, logg, and FeH from metadata.
    Falls back to config defaults [0.3, 0.3] if table is missing or star parameters are not found.
    """
    teff = meta.get('teff')
    logg = meta.get('logg')
    feh = meta.get('feh', 0.0) # default to solar metallicity if missing
    
    # If the metadata parameters are missing, return defaults
    if teff is None or np.isnan(teff) or logg is None or np.isnan(logg):
        return cfg.LD_DEFAULT[0], cfg.LD_DEFAULT[1]
        
    ld_table_path = Path(cfg.LD_TABLE_PATH)
    if not ld_table_path.exists():
        return cfg.LD_DEFAULT[0], cfg.LD_DEFAULT[1]
        
    try:
        df = _load_ld_table(str(ld_table_path))
        
        # Simple nearest neighbor lookup in Teff, logg, and FeH space
        # Assuming the table has columns: 'teff', 'logg', 'feh', 'u1', 'u2'
        if all(c in df.columns for c in ['teff', 'logg', 'u1', 'u2']):
            # If feh is present, filter or include in distance
            if 'feh' in df.columns:
                dist = (
                    ((df['teff'] - teff) / 1000.0)**2 +
                    (df['logg'] - logg)**2 +
                    (df['feh'] - feh)**2
                )
            else:
                dist = (
                    ((df['teff'] - teff) / 1000.0)**2 +
                    (df['logg'] - logg)**2
                )
            
            idx = dist.idxmin()
            u1 = float(df.loc[idx, 'u1'])
            u2 = float(df.loc[idx, 'u2'])
            return u1, u2
    except Exception as e:
        print(f"Error querying LD table for TIC {tic_id}: {e}")
        
    return cfg.LD_DEFAULT[0], cfg.LD_DEFAULT[1]
