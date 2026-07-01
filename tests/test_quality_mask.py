"""Tests for PREP-01: quality mask (NaN removal + TESS quality flags)."""

import numpy as np
from pipeline.preprocess.quality_mask import apply_quality_mask


def test_nan_removed_from_time():
    """NaN values in time array should be removed."""
    time = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
    flux = np.ones(5)
    flux_err = np.ones(5) * 0.001
    quality = np.zeros(5, dtype=np.int32)

    t, f, fe, q = apply_quality_mask(time, flux, flux_err, quality)
    assert len(t) == 4
    assert not np.any(np.isnan(t))
    assert 2 not in t  # idx 1 (nan) removed


def test_nan_removed_from_flux():
    """NaN values in flux array should be removed."""
    time = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    flux = np.array([1.0, np.nan, 1.0, np.nan, 1.0])
    flux_err = np.ones(5) * 0.001
    quality = np.zeros(5, dtype=np.int32)

    t, f, fe, q = apply_quality_mask(time, flux, flux_err, quality)
    assert len(t) == 3
    assert not np.any(np.isnan(f))


def test_nan_removed_from_flux_err():
    """NaN values in flux_err array should also be removed."""
    time = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    flux = np.ones(5)
    flux_err = np.array([0.001, np.nan, 0.001, 0.001, 0.001])
    quality = np.zeros(5, dtype=np.int32)

    t, f, fe, q = apply_quality_mask(time, flux, flux_err, quality)
    assert len(t) == 4
    assert not np.any(np.isnan(fe))


def test_quality_bitmask_filters_cadences():
    """Cadences with quality flags matching the bitmask should be removed."""
    n = 10
    time = np.arange(n, dtype=float)
    flux = np.ones(n)
    flux_err = np.ones(n) * 0.001
    # Set some quality flags: bit 1 (value 2) is "AttitudeTweak"
    quality = np.array([0, 2, 0, 0, 2, 0, 0, 0, 0, 0], dtype=np.int32)

    # bitmask=2 should filter out cadences with bit 1 set
    t, f, fe, q = apply_quality_mask(time, flux, flux_err, quality, bitmask=2)
    assert len(t) == 8
    # Indices 1 and 4 should be removed
    assert t[0] == 0
    assert t[1] == 2


def test_quality_none_preserves_all_cadences():
    """If quality is None, only NaN filtering should apply."""
    time = np.array([1.0, 2.0, 3.0])
    flux = np.ones(3)
    flux_err = np.ones(3) * 0.001

    t, f, fe, q = apply_quality_mask(time, flux, flux_err, None)
    assert len(t) == 3
    assert q is None


def test_bitmask_175_filters_tess_standard_flags():
    """Default bitmask 175 should filter common TESS anomalies.

    Bitmask 175 = 1+2+4+8+32+128:
      bit 0 (1): AttitudeTweak
      bit 1 (2): SafeMode
      bit 2 (4): CoarsePoint
      bit 3 (8): EarthPoint
      bit 5 (32): Desat
      bit 7 (128): ManualExclude
    """
    n = 7
    time = np.arange(n, dtype=float)
    flux = np.ones(n)
    flux_err = np.ones(n) * 0.001
    quality = np.array([0, 1, 2, 4, 8, 32, 128], dtype=np.int32)

    t, f, fe, q = apply_quality_mask(time, flux, flux_err, quality)
    # Only index 0 (quality=0) should survive
    assert len(t) == 1
    assert t[0] == 0


def test_output_arrays_are_consistent_length():
    """All output arrays should have the same length."""
    time = np.arange(20, dtype=float)
    flux = np.ones(20)
    flux[3] = np.nan
    flux_err = np.ones(20) * 0.001
    quality = np.zeros(20, dtype=np.int32)

    t, f, fe, q = apply_quality_mask(time, flux, flux_err, quality)
    assert len(t) == len(f) == len(fe) == len(q)
