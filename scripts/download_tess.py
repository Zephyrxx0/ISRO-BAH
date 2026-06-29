import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import lightkurve as lk
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path so we can import config/store
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pipeline.config as cfg
from pipeline.ingest.store import save_lc_npz

def download_star_all_sectors(tic_id):
    """Download all available TESS 2-min cadence SPOC light curves for a single target."""
    catalog_rows = []
    try:
        # Explicitly filter to 2-minute ('short') cadence to prevent multiple cadences 
        # within the same sector from overwriting each other.
        search = lk.search_lightcurve(f"TIC {tic_id}", author="SPOC", cadence="short")
        if len(search) == 0:
            return catalog_rows
        
        for res in search:
            # Extract sector from the 'mission' string (e.g., 'TESS Sector 01')
            mission_str = res.mission[0] if isinstance(res.mission, (list, tuple, np.ndarray)) else res.mission
            try:
                sector = int(mission_str.split()[-1])
            except ValueError:
                continue # Skip if we can't parse the sector
                
            lc = res.download()
            if lc is None:
                continue
                
            meta = {
                'tic_id': int(tic_id),
                'sector': int(sector),
                'teff': float(getattr(lc, 'TEFF', np.nan)),
                'logg': float(getattr(lc, 'LOGG', np.nan)),
                'feh': float(getattr(lc, 'FEH', np.nan)),
                'tmag': float(getattr(lc, 'TESSMAG', np.nan)),
                'ra': float(getattr(lc, 'ra', np.nan)),
                'dec': float(getattr(lc, 'dec', np.nan)),
                'download_status': 'SUCCESS',
                'exclusion_reason': 'NONE'
            }
            
            save_lc_npz(
                tic_id=tic_id,
                sector=sector,
                time=lc.time.value,
                flux=lc.flux.value,
                flux_err=lc.flux_err.value,
                quality=lc.quality,
                meta=meta,
                kind='raw'
            )
            catalog_rows.append(meta)
            
    except Exception as e:
        catalog_rows.append({
            "tic_id": int(tic_id),
            "download_status": "ERROR",
            "exclusion_reason": repr(e),
        })
        
    return catalog_rows

def download_batch(tic_ids, workers=5):
    print(f"Starting TESS download for {len(tic_ids)} targets (fetching all available sectors)...")
    all_catalog_rows = []
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(download_star_all_sectors, tic): tic for tic in tic_ids}
        for i, future in enumerate(as_completed(futures), 1):
            rows = future.result()
            all_catalog_rows.extend(rows)
            print(f"Processed {i}/{len(tic_ids)} targets. Downloaded {len(all_catalog_rows)} lightcurves total.")
                
    # Save the catalog
    if all_catalog_rows:
        cfg.CATALOGUE_DIR.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(all_catalog_rows)
        
        # Save master catalogue
        cat_path = cfg.MASTER_CATALOGUE_PATH
        if cat_path.exists():
            existing_df = pd.read_parquet(cat_path)
            df = pd.concat([existing_df, df]).drop_duplicates(subset=['tic_id', 'sector'])
            
        df.to_parquet(cat_path, index=False)
        print(f"Updated catalogue with {len(df)} entries at {cat_path}")
        
    return all_catalog_rows

if __name__ == "__main__":
    # Test subset of well-known exoplanet host stars
    example_tics = [
        22529346,   # WASP-121 
        307210830,  # L 98-59 
        259377017,  # TOI-270 
    ]
    
    print("Beginning download of TESS raw data...")
    download_batch(example_tics)
    
    print(f"\nDownload finished! Raw lightcurves are in: {cfg.RAW_DIR}")
    print(f"Catalogue created at: {cfg.MASTER_CATALOGUE_PATH}")
