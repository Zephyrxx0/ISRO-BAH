"""Tests for PREP-07: per-star limb darkening coefficient lookup."""

import numpy as np
import pipeline.config as cfg
from pipeline.preprocess.limb_darkening import get_ld_coefficients


def test_default_ld_returned_when_teff_is_none():
    """When teff is None, default LD coefficients should be returned."""
    meta = {"teff": None, "tic_id": 12345}
    result = get_ld_coefficients(12345, meta)
    assert result == cfg.LD_DEFAULT


def test_default_ld_returned_when_teff_is_nan():
    """When teff is NaN, default LD coefficients should be returned."""
    meta = {"teff": float("nan"), "tic_id": 12345}
    result = get_ld_coefficients(12345, meta)
    assert result == cfg.LD_DEFAULT


def test_default_ld_returned_when_teff_missing():
    """When meta dict lacks teff key, default LD should be returned."""
    meta = {"tic_id": 12345}
    result = get_ld_coefficients(12345, meta)
    assert result == cfg.LD_DEFAULT


def test_ld_lookup_from_parquet(mock_ld_parquet, monkeypatch):
    """When teff is valid, nearest-neighbor lookup should find coefficients."""
    # Override the config path to use our mock parquet
    monkeypatch.setattr(cfg, "LD_TABLE_PATH", str(mock_ld_parquet))

    meta = {"teff": 5000.0}
    result = get_ld_coefficients(12345, meta)
    # Should match the row with teff=5000
    assert result == [0.25, 0.20]


def test_ld_nearest_neighbor_interpolation(mock_ld_parquet, monkeypatch):
    """Nearest neighbor: teff 4800 should pick teff 5000 (closest)."""
    monkeypatch.setattr(cfg, "LD_TABLE_PATH", str(mock_ld_parquet))

    meta = {"teff": 4800.0}
    result = get_ld_coefficients(12345, meta)
    # |5000 - 4800| = 200, which is smaller than |4000 - 4800| = 800
    assert result == [0.25, 0.20]


def test_ld_returns_list_of_floats(mock_ld_parquet, monkeypatch):
    """Return value should be a list of two floats."""
    monkeypatch.setattr(cfg, "LD_TABLE_PATH", str(mock_ld_parquet))

    meta = {"teff": 6000.0}
    result = get_ld_coefficients(12345, meta)
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(v, float) for v in result)


def test_ld_fallback_on_missing_parquet(monkeypatch):
    """When parquet file doesn't exist, fall back to defaults."""
    monkeypatch.setattr(cfg, "LD_TABLE_PATH", "/nonexistent/path.parquet")

    meta = {"teff": 5000.0}
    result = get_ld_coefficients(12345, meta)
    assert result == cfg.LD_DEFAULT
