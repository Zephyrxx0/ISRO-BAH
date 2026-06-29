import numpy as np

def apply_quality_mask(time, flux, flux_err, quality, bitmask=175):
    """
    Remove NaNs and quality-flagged cadences.
    TESS standard bitmask 175 filters common systematic/hardware anomalies.
    """
    # Create mask for valid data points (no NaNs in time or flux)
    valid = (~np.isnan(time)) & (~np.isnan(flux)) & (~np.isnan(flux_err))
    
    # Apply quality bitmask: if any bit in bitmask is set in quality, discard
    if quality is not None:
        valid = valid & ((quality & bitmask) == 0)
        
    return time[valid], flux[valid], flux_err[valid], quality[valid] if quality is not None else None
