import numpy as np
from astropy.stats import sigma_clip

def apply_sigma_clip(time, flux, flux_err, sigma=5.0):
    """
    Perform 5σ sigma clipping to remove outliers and normalize flux by the median.
    """
    clipped = sigma_clip(flux, sigma=sigma, maxiters=5)
    mask = ~np.ma.getmaskarray(clipped)
    
    clean_time = time[mask]
    clean_flux = flux[mask]
    clean_flux_err = flux_err[mask]
    
    median_val = np.nanmedian(clean_flux)
    if median_val > 0:
        clean_flux = clean_flux / median_val
        clean_flux_err = clean_flux_err / median_val
        
    return clean_time, clean_flux, clean_flux_err, mask
