import os
import pandas as pd
import requests
import lightkurve as lk
from pathlib import Path
import pipeline.config as cfg
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_kepler_tce_catalog():
    """Download the Kepler DR24 TCE catalog from NASA Exoplanet Archive TAP service."""
    out_path = Path(cfg.KEPLER_TCE_PATH)
    if out_path.exists():
        print(f"Loading Kepler TCE catalog from cache: {out_path}")
        return pd.read_csv(out_path)
    
    print("Downloading Kepler DR24 TCE catalog from NASA Exoplanet Archive...")
    # TAP query for Q1-Q17 DR24 TCE catalog
    url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+kepid,tce_plnt_num,tce_period,tce_time0bk,tce_duration,tce_depth,av_training_set+from+q1_q17_dr24_tce&format=csv"
    
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(response.text)
        
    df = pd.read_csv(out_path)
    # Rename av_training_set to label_class for consistency in notebooks if needed
    if 'av_training_set' in df.columns:
        df['label_class'] = df['av_training_set']
    return df

def _download_single_kic(kic_id, dest_dir):
    """Download lightcurve for a single KIC ID and save as .npz."""
    try:
        dest_path = dest_dir / f"{kic_id}_kepler.npz"
        if dest_path.exists():
            return "EXISTS"
            
        # Search Kepler light curves (using long cadence)
        search_result = lk.search_lightcurve(f"KIC {kic_id}", mission="Kepler", cadence="long")
        if len(search_result) == 0:
            return "NOT_FOUND"
            
        # Download all available quarters and stitch them
        lc_collection = search_result.download_all()
        if lc_collection is None or len(lc_collection) == 0:
            return "DOWNLOAD_FAILED"
            
        lc = lc_collection.stitch()
        
        # Save arrays and metadata to npz
        import numpy as np
        meta = {
            'kic_id': kic_id,
            'ra': getattr(lc, 'ra', None),
            'dec': getattr(lc, 'dec', None),
        }
        np.savez_compressed(
            str(dest_path),
            time=lc.time.value,
            flux=lc.flux.value,
            flux_err=lc.flux_err.value,
            quality=lc.quality,
            meta=meta
        )
        return "SUCCESS"
    except Exception as e:
        return f"ERROR: {str(e)}"

def download_kepler_lightcurves(kic_ids, limit=None, workers=4):
    """Download Kepler light curves for listed KIC IDs and save to npz files."""
    dest_dir = cfg.OUTPUTS_DIR / 'kepler'
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    targets = kic_ids[:limit] if limit is not None else kic_ids
    print(f"Downloading {len(targets)} Kepler light curves using {workers} workers...")
    
    counts = {"SUCCESS": 0, "EXISTS": 0, "NOT_FOUND": 0, "DOWNLOAD_FAILED": 0, "ERROR": 0}
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_download_single_kic, kic, dest_dir): kic for kic in targets}
        for i, future in enumerate(as_completed(futures), 1):
            kic = futures[future]
            try:
                res = future.result()
                if res.startswith("ERROR"):
                    counts["ERROR"] += 1
                else:
                    counts[res] += 1
            except Exception as e:
                counts["ERROR"] += 1
            
            if i % 10 == 0 or i == len(targets):
                print(f"Downloaded {i}/{len(targets)} targets. Current counts: {counts}")
                
    return counts
