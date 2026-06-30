import numpy as np
import wotan

def apply_biweight_detrend(time, flux, window_length=0.75):
    """
    Detrend the light curve using wotan's biweight estimator.
    """
    # Ensure window_length is smaller than the duration of the data
    span = time[-1] - time[0] if len(time) > 1 else 0
    if span < window_length:
        window_length = span / 2.0 if span > 0 else 0.1
        
    flat_flux, trend = wotan.flatten(
        time, flux,
        window_length=window_length,
        method='biweight',
        return_trend=True
    )
    return flat_flux, trend

def validate_transit_preservation(time, flux, period, t0, duration_days, expected_depth, label='Target'):
    """
    Validate that detrending has not erased or significantly attenuated the transit depth.
    Calculates in-transit vs out-of-transit median level of folded light curve.
    """
    phase = ((time - t0) % period) / period
    phase[phase > 0.5] -= 1.0
    
    # Calculate duration in phase space
    half_dur_phase = (duration_days / period) / 2.0
    
    in_transit = np.abs(phase) <= half_dur_phase
    # Out of transit is defined in a buffer zone near the transit
    out_transit = (np.abs(phase) > half_dur_phase) & (np.abs(phase) <= 3.0 * half_dur_phase)
    
    if np.sum(in_transit) < 3 or np.sum(out_transit) < 3:
        # Not enough data points to measure
        return False
        
    median_in = np.median(flux[in_transit])
    median_out = np.median(flux[out_transit])
    
    measured_depth = median_out - median_in
    
    # Aligns with depth preservation check. We allow up to 30% attenuation.
    passed = measured_depth >= 0.7 * expected_depth
    print(f"[{label}] Expected depth: {expected_depth:.5f}, Measured: {measured_depth:.5f}. Status: {'PASSED' if passed else 'FAILED'}")
    return passed
