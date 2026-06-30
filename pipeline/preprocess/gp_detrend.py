import numpy as np
import celerite2
from celerite2 import terms


def apply_gp_detrend(time, flux, flux_err, jitter=1e-6):
    """
    Apply Gaussian Process detrending using celerite2 Matern-3/2 kernel.
    Models correlated (red) noise for top SDE >= 7 candidates.
    Returns detrended flux and the GP trend.

    PREP-04: celerite2 Matern-3/2 on top 100 SDE >= 7 candidates.
    """
    if len(time) < 100:
        return flux, np.zeros_like(flux)

    median_flux = np.nanmedian(flux)
    y = flux - median_flux

    kernel = terms.Matern32Term(
        sigma=np.nanstd(y) * 0.5,
        rho=np.ptp(time) * 0.1
    )
    yerr = np.sqrt(flux_err**2 + jitter**2)

    gp = celerite2.GaussianProcess(kernel, mean=0.0)
    gp.compute(time, yerr=yerr)

    mu = gp.predict(y, time, return_cov=False)
    trend = mu + median_flux
    detrended_flux = flux - mu

    return detrended_flux, trend
