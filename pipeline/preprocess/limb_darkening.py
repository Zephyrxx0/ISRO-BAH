import pandas as pd
import numpy as np
import pipeline.config as cfg

def get_ld_coefficients(tic_id, meta):
    """
    Retrieve quadratic limb darkening coefficients (u1, u2) using a 1D 
    nearest-neighbor lookup on effective temperature (Teff) against the Claret table.
    """
    teff = meta.get('teff')
    if teff is None or np.isnan(teff):
        return cfg.LD_DEFAULT
        
    try:
        df = pd.read_parquet(str(cfg.LD_TABLE_PATH))
        if df.empty:
            return cfg.LD_DEFAULT
            
        # 1D nearest neighbor lookup over Teff dimension only
        idx = (df['teff'] - teff).abs().idxmin()
        row = df.loc[idx]
        
        return [float(row['u1']), float(row['u2'])]
        
    except Exception as e:
        print(f"Warning: Limb darkening lookup failed for TIC {tic_id} ({e}). Using defaults.")
        return cfg.LD_DEFAULT
