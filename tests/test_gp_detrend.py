"""Tests for PREP-04: Gaussian Process detrending (celerite2)."""

import numpy as np
import pytest
from pipeline.preprocess.gp_detrend import apply_gp_detrend


def test_gp_detrend_output_shapes():
    """GP detrend should return arrays of same length as input."""
    np.random.seed(42)
    n = 500
    time = np.linspace(0, 27, n)
    flux = 1.0 + np.sin(time * 0.5) * 0.01 + np.random.normal(0, 0.001, n)
    flux_err = np.full(n, 0.001)

    detrended, trend = apply_gp_detrend(time, flux, flux_err)

    assert len(detrended) == n
    assert len(trend) == n


def test_gp_detrend_reduces_variance():
    """GP detrended flux should have lower variance than raw flux with trend."""
    np.random.seed(42)
    n = 500
    time = np.linspace(0, 27, n)
    flux = 1.0 + np.sin(time * 0.5) * 0.02 + np.random.normal(0, 0.002, n)
    flux_err = np.full(n, 0.001)

    detrended, trend = apply_gp_detrend(time, flux, flux_err)

    assert np.std(detrended) < np.std(flux)


def test_gp_detrend_short_series_returns_input():
    """Very short time series (< 100 points) should return flux unchanged."""
    np.random.seed(42)
    n = 50
    time = np.linspace(0, 5, n)
    flux = np.ones(n) + np.random.normal(0, 0.001, n)
    flux_err = np.full(n, 0.001)

    detrended, trend = apply_gp_detrend(time, flux, flux_err)

    np.testing.assert_array_equal(detrended, flux)
    np.testing.assert_array_equal(trend, np.zeros_like(flux))


def test_gp_detrend_trend_is_not_all_zero():
    """For sufficient data, trend should be non-trivial (not all zeros)."""
    np.random.seed(42)
    n = 500
    time = np.linspace(0, 27, n)
    flux = 1.0 + np.sin(time * 0.5) * 0.01 + np.random.normal(0, 0.001, n)
    flux_err = np.full(n, 0.001)

    detrended, trend = apply_gp_detrend(time, flux, flux_err)

    assert np.std(trend) > 0
