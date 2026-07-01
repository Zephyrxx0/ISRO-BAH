import numpy as np
from astropy.timeseries import BoxLeastSquares

def validate_candidates(candidates, lc_data):
    """
    Validate TLS candidates using Box Least Squares (BLS).
    Checks if BLS finds a transit signal at a similar period (within 2%).
    """
    for r in candidates:
        key = (int(r['tic_id']), int(r['sector']))
        if key not in lc_data:
            r['bls_consistent'] = False
            continue
            
        lc = lc_data[key]
        time = lc['time']
        flux = lc['flux']
        flux_err = lc['flux_err']
        
        # Mask out gap points if present
        gap_mask = lc.get('gap_mask', np.zeros(len(time), dtype=bool))
        time = time[~gap_mask]
        flux = flux[~gap_mask]
        flux_err = flux_err[~gap_mask]
        
        if len(time) < 100:
            r['bls_consistent'] = False
            continue
            
        tls_period = r['period']
        tls_duration = r['duration']
        
        try:
            # Set up BLS model
            # Note: astropy BLS expects flux centered at 0 or raw flux (handles either)
            bls = BoxLeastSquares(time, flux, dy=flux_err)
            
            # Search period space restricted around the TLS candidate period
            p_min = max(0.1, 0.95 * tls_period)
            p_max = 1.05 * tls_period
            
            periods = np.linspace(p_min, p_max, 500)
            durations = [tls_duration]
            
            results = bls.power(periods, durations)
            
            best_period = results.period[np.argmax(results.power)]
            
            # Check consistency within 2%
            diff = np.abs(best_period - tls_period) / tls_period
            r['bls_consistent'] = bool(diff < 0.02)
        except Exception as e:
            print(f"BLS validation error for TIC {r['tic_id']}: {e}")
            r['bls_consistent'] = False
            
    return candidates
