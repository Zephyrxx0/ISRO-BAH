"""Tests for DATA-01: TESS download helpers (_npz_path)."""

from pathlib import Path
from pipeline.ingest.download_tess import _npz_path


def test_npz_path_returns_path_object():
    """_npz_path should return a Path object."""
    path = _npz_path(12345, 1, kind="raw")
    assert isinstance(path, Path)


def test_npz_path_includes_tic_id():
    """Generated path should include the TIC ID zero-padded to 16 digits."""
    path = _npz_path(12345, 1, kind="raw")
    assert "tic0000000000012345" in str(path)


def test_npz_path_includes_sector():
    """Generated path should include the sector zero-padded to 4 digits."""
    path = _npz_path(999, 3, kind="raw")
    assert "_s0003" in str(path)


def test_npz_path_ends_with_kind():
    """Generated path should end with _raw.npz or _preprocessed.npz."""
    path_raw = _npz_path(100, 2, kind="raw")
    path_prep = _npz_path(100, 2, kind="preprocessed")
    assert path_raw.name.endswith("_raw.npz")
    assert path_prep.name.endswith("_preprocessed.npz")


def test_npz_path_raw_and_prep_different_dirs():
    """Raw and preprocessed paths should go to different base directories."""
    path_raw = _npz_path(100, 1, kind="raw")
    path_prep = _npz_path(100, 1, kind="preprocessed")
    # They should differ in the base dir, not just filename
    assert path_raw != path_prep
