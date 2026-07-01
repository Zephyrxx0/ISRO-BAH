"""Tests for completeness injection logic (VIS-03)."""

import numpy as np
import pytest

from src.characterization.completeness import _inject_transit


def test_inject_transit_reduces_flux_at_transit():
    """Injected transit creates a detectable flux dip."""
    np.random.seed(42)
    time = np.linspace(0, 10, 5000)
    flux = np.ones_like(time)
    period = 3.0
    depth_ppm = 500.0

    injected, params = _inject_transit(time, flux, period, depth_ppm)

    assert isinstance(injected, np.ndarray)
    assert isinstance(params, dict)
    assert "period" in params
    assert params["period"] == period
    assert params["depth_ppm"] == depth_ppm
    # Flux should dip below original baseline somewhere
    # 500 ppm depth = ~0.0005 dip from 1.0 → min flux ~0.9995
    assert np.min(injected) < 0.9996


def test_inject_transit_depth_scales_with_ppm():
    """Larger depth_ppm produces a deeper flux dip."""
    np.random.seed(42)
    time = np.linspace(0, 10, 5000)
    flux = np.ones_like(time)

    injected_shallow, _ = _inject_transit(time, flux.copy(), 3.0, 100.0)
    injected_deep, _ = _inject_transit(time, flux.copy(), 3.0, 2000.0)

    # Deeper injection should have lower minimum flux
    assert np.min(injected_deep) < np.min(injected_shallow)


def test_inject_transit_preserves_signal_length():
    """Output has same length as input."""
    np.random.seed(42)
    time = np.linspace(0, 10, 1000)
    flux = np.ones(1000)

    injected, _ = _inject_transit(time, flux, 2.0, 500.0)
    assert len(injected) == len(flux)


def test_inject_transit_returns_valid_rp_rs():
    """rp_rs is sqrt(depth in fractional units)."""
    np.random.seed(42)
    time = np.linspace(0, 10, 1000)
    flux = np.ones(1000)

    _, params = _inject_transit(time, flux, 3.0, 1000.0)
    expected_rp = np.sqrt(1000e-6)
    assert params["rp_rs"] == pytest.approx(expected_rp)


def test_inject_transit_uses_random_t0():
    """Two calls produce different t0 values (randomized)."""
    np.random.seed(99)
    time = np.linspace(0, 10, 1000)
    flux = np.ones(1000)

    _, params1 = _inject_transit(time, flux, 3.0, 500.0)
    _, params2 = _inject_transit(time, flux, 3.0, 500.0)

    # Different random seeds -> likely different t0
    # With seed 99, two consecutive calls should differ
    assert params1["t0"] != params2["t0"]
