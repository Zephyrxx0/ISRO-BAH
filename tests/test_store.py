"""Tests for DATA-05: .npz storage (npz_path, save_lc_npz, load_lc_npz)."""

import numpy as np
import json
from pathlib import Path
from pipeline.ingest.store import npz_path, save_lc_npz, load_lc_npz


def test_npz_path_generates_raw_path_correctly():
    """npz_path should generate the correct Path for raw kind."""
    path = npz_path(12345, 1, kind="raw")
    assert isinstance(path, Path)
    assert "tic0000000000012345" in str(path)
    assert "_s0001" in str(path)
    assert path.name.endswith("_raw.npz")


def test_npz_path_generates_preprocessed_path():
    """npz_path should use PREP_DIR for kind='preprocessed'."""
    path = npz_path(12345, 1, kind="preprocessed")
    assert "preprocessed" in str(path) or path.name.endswith("_preprocessed.npz")


def test_npz_path_formats_large_tic_id():
    """Large TIC IDs should be zero-padded to 16 digits."""
    path = npz_path(307210830, 1, kind="raw")
    assert "tic0000000307210830" in str(path)


def test_save_and_load_roundtrip(tmp_npz_dir, monkeypatch):
    """Saving and loading should preserve all data arrays."""
    import pipeline.config as cfg
    monkeypatch.setattr(cfg, "RAW_DIR", tmp_npz_dir)

    tic_id = 99999
    sector = 1
    time = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    flux = np.array([0.99, 1.01, 0.98, 1.00, 1.02])
    flux_err = np.array([0.001, 0.001, 0.001, 0.001, 0.001])
    quality = np.array([0, 0, 0, 0, 0], dtype=np.int32)
    meta = {"tic_id": tic_id, "sector": sector, "ra": 83.5, "dec": -22.0, "tmag": 10.5}

    path = save_lc_npz(tic_id, sector, time, flux, flux_err, quality, meta, kind="raw")
    assert path.exists()

    loaded = load_lc_npz(tic_id, sector, kind="raw")
    np.testing.assert_array_equal(loaded["time"], time)
    np.testing.assert_array_equal(loaded["flux"], flux)
    np.testing.assert_array_equal(loaded["flux_err"], flux_err)
    assert loaded["meta"]["tic_id"] == tic_id
    assert loaded["meta"]["tmag"] == 10.5


def test_load_nonexistent_file_raises():
    """Loading a nonexistent .npz should raise FileNotFoundError."""
    with np.testing.assert_raises(FileNotFoundError):
        load_lc_npz(0, 0, kind="raw")


def test_meta_serialized_as_json(tmp_npz_dir, monkeypatch):
    """The meta dictionary should be serialized as JSON within the npz."""
    import pipeline.config as cfg
    monkeypatch.setattr(cfg, "RAW_DIR", tmp_npz_dir)

    tic_id = 42
    meta = {"key": "value", "nested": {"a": 1, "b": [2, 3]}}
    save_lc_npz(tic_id, 1, np.array([1.0]), np.array([1.0]),
                np.array([0.001]), np.array([0]), meta, kind="raw")

    loaded = load_lc_npz(tic_id, 1, kind="raw")
    assert loaded["meta"] == meta
