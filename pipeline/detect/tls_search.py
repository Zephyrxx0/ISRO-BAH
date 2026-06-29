import os
import json
import numpy as np
from pathlib import Path
import pipeline.config as cfg
from pipeline.ingest.store import load_lc_npz
from transitleastsquares import transitleastsquares, transit_mask
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

CHECKPOINT_PATH = cfg.OUTPUTS_DIR / 'tls_checkpoint.json'

def run_tls_single(args):
    """Run TLS search for a single star. Returns a list of result dicts (one per planet/iteration)."""
    tic_id, sector, u1, u2 = args
    results = []
    
    try:
        lc = load_lc_npz(tic_id, sector, kind='preprocessed')
        time = lc['time']
        flux = lc['flux']
        flux_err = lc['flux_err']
        
        # Check if gap_mask exists in the file, if so we should mask or use it
        gap_mask = lc.get('gap_mask', np.zeros(len(time), dtype=bool))
        # Exclude gap-edge data from period search
        time = time[~gap_mask]
        flux = flux[~gap_mask]
        flux_err = flux_err[~gap_mask]
        
        if len(time) < 100:
            return results
            
        current_flux = flux.copy()
        
        for i in range(1, cfg.TLS_ITERATIONS + 1):
            model = transitleastsquares(time, current_flux, flux_err)
            # Run search with config parameters
            res = model.power(
                period_min=cfg.TLS_PERIOD_MIN,
                period_max=cfg.TLS_PERIOD_MAX,
                oversampling_factor=cfg.TLS_OVERSAMPLING,
                u=[u1, u2]
            )
            
            # If SDE is too low or not valid, stop search
            if not hasattr(res, 'SDE') or np.isnan(res.SDE) or res.SDE < 1.0:
                break
                
            res_dict = {
                'tic_id': int(tic_id),
                'sector': int(sector),
                'planet_num': i,
                'period': float(res.period),
                't0': float(res.T0),
                'duration': float(res.duration),
                'depth': float(res.depth),
                'sde': float(res.SDE),
                'snr': float(res.snr),
                'cdpp': float(getattr(res, 'cdpp', 0.0)),
                'chi2': float(getattr(res, 'chi2', 0.0)),
                'chi2_red': float(getattr(res, 'chi2_red', 0.0))
            }
            results.append(res_dict)
            
            # If the SDE is below the discard threshold, no need to look for further planets
            if res.SDE < cfg.SDE_DISCARD:
                break
                
            # Mask the found planet and search for the next one
            mask = transit_mask(time, res.period, res.duration, res.T0)
            current_flux[mask] = 1.0
            
    except Exception as e:
        print(f"Error running TLS for TIC {tic_id} Sector {sector}: {e}")
        
    return results

def run_tls_batch(star_list, workers=None):
    """Run TLS search on list of stars with multiprocessing and checkpointing."""
    if workers is None:
        workers = mp.cpu_count()
        
    checkpoint_file = Path(CHECKPOINT_PATH)
    completed_keys = set()
    all_results = []
    
    # Load checkpoint if exists
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r') as f:
                saved = json.load(f)
                all_results = saved.get('results', [])
                completed_keys = set(tuple(x) for x in saved.get('completed', []))
                print(f"Resuming TLS batch from checkpoint. {len(completed_keys)} stars already processed.")
        except Exception as e:
            print(f"Failed to load checkpoint: {e}")
            
    # Filter out already processed stars
    to_process = [s for s in star_list if (s[0], s[1]) not in completed_keys]
    
    if not to_process:
        print("All stars already processed in checkpoint.")
        return all_results
        
    print(f"Running TLS on {len(to_process)} stars with {workers} processes...")
    
    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(run_tls_single, star): (star[0], star[1]) for star in to_process}
            
            for idx, future in enumerate(as_completed(futures), 1):
                key = futures[future]
                try:
                    res_list = future.result()
                    all_results.extend(res_list)
                    completed_keys.add(key)
                except Exception as e:
                    print(f"Process error for key {key}: {e}")
                
                # Checkpoint every 100 stars or at the end
                if idx % 100 == 0 or idx == len(to_process):
                    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(checkpoint_file, 'w') as f:
                        json.dump({
                            'completed': list(completed_keys),
                            'results': all_results
                        }, f)
                    print(f"TLS progress checkpointed: {idx}/{len(to_process)} stars done.")
                    
    except KeyboardInterrupt:
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(checkpoint_file, 'w') as f:
            json.dump({
                'completed': list(completed_keys),
                'results': all_results,
            }, f)
        print("Interrupted! Checkpoint saved.")
        
    return all_results
