"""Tests for VAL-01 & VAL-02: smoke test validation of benchmark planets."""

import pandas as pd
import pytest
from pathlib import Path
from pipeline.validate.smoke_test import BENCHMARKS, run_smoke_test


def test_benchmarks_has_three_systems():
    """BENCHMARKS dict should contain all 3 benchmark systems."""
    assert "WASP-121b" in BENCHMARKS
    assert "L 98-59" in BENCHMARKS
    assert "TOI-270" in BENCHMARKS


def test_benchmarks_has_seven_planets_total():
    """All 3 systems should sum to 7 known planets."""
    total = sum(len(info["periods"]) for info in BENCHMARKS.values())
    assert total == 7


def test_benchmarks_have_tic_ids():
    """Every benchmark system should have a tic_id."""
    for system, info in BENCHMARKS.items():
        assert "tic_id" in info
        assert isinstance(info["tic_id"], int)
        assert "periods" in info
        assert len(info["periods"]) > 0


def test_run_smoke_test_nonexistent_path():
    """run_smoke_test should return False if catalogue doesn't exist."""
    result = run_smoke_test("/nonexistent/path/to/catalogue.parquet")
    assert result is False


def test_run_smoke_test_with_matching_catalogue(tmp_path):
    """run_smoke_test should pass when all planets are present in catalogue."""
    # Create a dataframe with all 7 benchmark planets
    rows = []
    for system, info in BENCHMARKS.items():
        for period in info["periods"]:
            rows.append({
                "tic_id": info["tic_id"],
                "period": period,
                "disposition": "FULL_PIPELINE",
                "sde": 10.0,
            })

    df = pd.DataFrame(rows)
    path = tmp_path / "test_catalogue.parquet"
    df.to_parquet(path)

    result = run_smoke_test(str(path))
    assert result is True


def test_run_smoke_test_missing_planet_fails(tmp_path):
    """run_smoke_test should return False when a planet is missing."""
    # Only include 6 of 7 planets
    rows = []
    for system, info in BENCHMARKS.items():
        periods = info["periods"][:-1] if len(info["periods"]) > 1 else info["periods"]
        for period in periods:
            rows.append({
                "tic_id": info["tic_id"],
                "period": period,
                "disposition": "FULL_PIPELINE",
                "sde": 10.0,
            })

    if len(rows) == 7:
        # Remove one row to make it 6
        rows.pop()

    df = pd.DataFrame(rows)
    path = tmp_path / "test_missing.parquet"
    df.to_parquet(path)

    result = run_smoke_test(str(path))
    assert result is False


def test_run_smoke_test_discarded_planets_not_counted(tmp_path):
    """Planets with DISCARD disposition should not count as recovered."""
    # Create a planet with DISCARD disposition
    rows = [{
        "tic_id": 22529346,  # WASP-121b
        "period": 1.27492,
        "disposition": "DISCARD",
        "sde": 3.0,
    }]
    df = pd.DataFrame(rows)
    path = tmp_path / "test_discarded.parquet"
    df.to_parquet(path)

    result = run_smoke_test(str(path))
    # WASP-121b exists but is DISCARDED → should fail
    assert result is False
