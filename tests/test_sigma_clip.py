"""Tests for PREP-02: sigma clipping and flux normalization."""

import numpy as np
from pipeline.preprocess.sigma_clip import apply_sigma_clip


def test_sigma_clip_removes_extreme_outliers():
    """5-sigma clipping should remove points far from the median."""
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 27, n)
    flux = np.ones(n) + np.random.normal(0, 0.001, n)
    # Inject a massive outlier
    flux[500] = 100.0
    flux_err = np.full(n, 0.001)

    t, f, fe, mask = apply_sigma_clip(time, flux, flux_err)

    # The outlier at index 500 should be removed
    assert len(f) < n
    assert not np.any(f > 10.0)


def test_sigma_clip_preserves_normal_data_length():
    """Clean data should have most points preserved after sigma clipping."""
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 27, n)
    flux = 1.0 + np.random.normal(0, 0.0005, n)
    flux_err = np.full(n, 0.0005)

    t, f, fe, mask = apply_sigma_clip(time, flux, flux_err)

    # With 5-sigma clipping, most points should survive
    assert len(f) >= n * 0.95


def test_sigma_clip_normalizes_flux():
    """After sigma clipping, flux should be normalized to median ~1.0."""
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 27, n)
    flux = 10.0 + np.random.normal(0, 0.005, n)  # median ~10
    flux_err = np.full(n, 0.005)

    t, f, fe, mask = apply_sigma_clip(time, flux, flux_err)

    median = np.nanmedian(f)
    assert np.abs(median - 1.0) < 0.01


def test_sigma_clip_returns_mask():
    """apply_sigma_clip should return a boolean mask where True = kept."""
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 27, n)
    flux = np.ones(n) + np.random.normal(0, 0.001, n)
    # Inject massive outlier — 10σ above median
    flux[500] = 100.0
    flux_err = np.full(n, 0.001)

    t, f, fe, mask = apply_sigma_clip(time, flux, flux_err)

    assert mask.dtype == bool
    assert len(mask) == len(time)
    # The outlier point should be masked out (excluded = False in mask)
    assert bool(mask[500]) is False


def test_sigma_clip_output_arrays_consistent():
    """All output arrays should have the same length."""
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 27, n)
    flux = 1.0 + np.random.normal(0, 0.001, n)
    flux_err = np.full(n, 0.001)

    t, f, fe, mask = apply_sigma_clip(time, flux, flux_err)
    assert len(t) == len(f) == len(fe)


def test_sigma_clip_with_negative_median():
    """If median is 0 or negative, flux should not be divided (avoid div by 0)."""
    time = np.array([1.0, 2.0, 3.0])
    flux = np.array([0.0, 0.0, 0.0])
    flux_err = np.array([0.001, 0.001, 0.001])

    t, f, fe, mask = apply_sigma_clip(time, flux, flux_err)
    # Should not crash, and flux should be unchanged (median <= 0)
    assert len(t) == 3
