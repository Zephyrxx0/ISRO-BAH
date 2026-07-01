"""Tests for PREP-03: biweight detrend with transit preservation."""

import numpy as np
from pipeline.preprocess.detrend import apply_biweight_detrend, validate_transit_preservation


def test_biweight_detrend_output_shape():
    """apply_biweight_detrend should return flat_flux and trend arrays of same length."""
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 27, n)
    flux = 1.0 + np.sin(time * 0.5) * 0.01 + np.random.normal(0, 0.001, n)

    flat_flux, trend = apply_biweight_detrend(time, flux)

    assert len(flat_flux) == n
    assert len(trend) == n
    assert flat_flux.shape == flux.shape


def test_biweight_detrend_removes_trend():
    """After detrending, the flux should be centered around zero."""
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 27, n)
    # Inject a strong sinusoidal trend
    flux = 1.0 + np.sin(time * 0.5) * 0.05 + np.random.normal(0, 0.001, n)

    flat_flux, trend = apply_biweight_detrend(time, flux)

    # The trended signal should have larger std than detrended
    assert np.std(flat_flux) < np.std(flux)


def test_biweight_detrend_short_span():
    """When span < window_length, window should be adjusted to span/2."""
    time = np.linspace(0, 0.5, 100)  # span = 0.5 days
    flux = np.ones(100) + np.random.normal(0, 0.001, 100)

    flat_flux, trend = apply_biweight_detrend(time, flux, window_length=0.75)

    assert len(flat_flux) == 100


def test_validate_transit_preservation_detects_known_transit():
    """A known transit injected into flat flux should be validated."""
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 30, n)
    flux = np.ones(n)
    # Inject transit
    period = 3.0
    duration = 0.125
    depth = 0.005
    t0 = 1.5
    for epoch in range(11):
        center = t0 + epoch * period
        in_transit = np.abs(time - center) < duration / 2
        flux[in_transit] -= depth

    result = validate_transit_preservation(
        time, flux, period, t0, duration_days=duration, expected_depth=depth
    )
    assert bool(result) is True


def test_validate_transit_preservation_rejects_wrong_transit():
    """Wrong period should fail transit preservation validation."""
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 30, n)
    flux = np.ones(n) + np.random.normal(0, 0.001, n)
    # No transit injected - should fail validation
    result = validate_transit_preservation(
        time, flux, period=5.0, t0=1.0, duration_days=0.1, expected_depth=0.005
    )
    assert bool(result) is False
