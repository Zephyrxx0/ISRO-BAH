"""Tests for Phase 3 shared utilities (PARM-06)."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.characterization.utils import (
    append_to_parquet,
    compute_a_rs,
    ensure_directories,
    filter_gate1_candidates,
    filter_gate2_candidates,
    get_limb_darkening,
    load_phase_folded,
    log_jsonl,
)


# ---------------------------------------------------------------------------
# compute_a_rs
# ---------------------------------------------------------------------------

def test_compute_a_rs_earth_solar():
    """Earth at 1 AU gives a/Rs ~215 for Sun-like star."""
    a_rs = compute_a_rs(365.25, 1.0, 1.0)
    # Earth's a/Rs = 215.0 (1 AU / 1 Rsol)
    assert 210 < a_rs < 220


def test_compute_a_rs_scales_with_mass():
    """Higher stellar mass > larger orbit > larger a/Rs (period fixed)."""
    a_low = compute_a_rs(10.0, 0.5, 1.0)
    a_high = compute_a_rs(10.0, 2.0, 1.0)
    assert a_high > a_low


def test_compute_a_rs_hot_jupiter():
    """Hot Jupiter at 3.5 day orbit around 1 Msol, 1 Rsol."""
    a_rs = compute_a_rs(3.5, 1.0, 1.0)
    # Hot Jupiter a/Rs typically 4-15
    assert 4 < a_rs < 20


# ---------------------------------------------------------------------------
# get_limb_darkening
# ---------------------------------------------------------------------------

@pytest.fixture
def ld_catalogue():
    """DataFrame with tic_id, ld_u1, ld_u2 for LD lookup tests."""
    return pd.DataFrame({
        "tic_id": [100, 200, 300],
        "ld_u1": [0.35, 0.30, np.nan],
        "ld_u2": [0.25, 0.22, np.nan],
    })


def test_get_limb_darkening_found(ld_catalogue):
    """Returns [u1, u2] when TIC ID is in catalogue with valid values."""
    ld = get_limb_darkening(100, ld_catalogue)
    assert ld == [0.35, 0.25]
    assert isinstance(ld[0], float)
    assert isinstance(ld[1], float)


def test_get_limb_darkening_nan_fallback(ld_catalogue):
    """Returns default [0.4, 0.2] when coefficients are NaN."""
    ld = get_limb_darkening(300, ld_catalogue)
    assert ld == [0.4, 0.2]


def test_get_limb_darkening_missing_tic(ld_catalogue):
    """Returns default [0.4, 0.2] when TIC ID not found."""
    ld = get_limb_darkening(999, ld_catalogue)
    assert ld == [0.4, 0.2]


def test_get_limb_darkening_missing_columns():
    """Returns default [0.4, 0.2] when ld_u1/ld_u2 columns missing."""
    df = pd.DataFrame({"tic_id": [100], "teff": [5000]})
    ld = get_limb_darkening(100, df)
    assert ld == [0.4, 0.2]


# ---------------------------------------------------------------------------
# filter_gate1_candidates
# ---------------------------------------------------------------------------

@pytest.fixture
def gate_catalogue():
    """Catalogue with candidates spanning Gate 1/2 thresholds."""
    return pd.DataFrame({
        "tic_id": [1, 2, 3, 4, 5],
        "tls_sde": [8.5, 6.0, 9.0, 7.0, 3.5],
        "pc_confidence": [0.92, 0.88, 0.65, 0.71, 0.50],
        "sector": [1, 1, 1, 1, 1],
    })


def test_filter_gate1_sde_lt_7_excluded(gate_catalogue):
    """Candidates with SDE < 7 are excluded from Gate 1."""
    result = filter_gate1_candidates(gate_catalogue)
    assert 2 not in result["tic_id"].values  # SDE=6.0
    assert 5 not in result["tic_id"].values  # SDE=3.5


def test_filter_gate1_confidence_le_070_excluded(gate_catalogue):
    """Candidates with pc_confidence <= 0.70 are excluded from Gate 1."""
    result = filter_gate1_candidates(gate_catalogue)
    assert 3 not in result["tic_id"].values  # confidence=0.65


def test_filter_gate1_passing_candidates(gate_catalogue):
    """Gate 1 admits SDE>=7 AND confidence>0.70."""
    result = filter_gate1_candidates(gate_catalogue)
    passing = set(result["tic_id"].values)
    assert 1 in passing  # SDE=8.5, conf=0.92
    assert 4 in passing  # SDE=7.0, conf=0.71
    assert len(result) == 2


def test_filter_gate1_boundary_sde_exactly_7(gate_catalogue):
    """SDE exactly 7 is included (>= operator)."""
    result = filter_gate1_candidates(gate_catalogue)
    assert 4 in result["tic_id"].values


# ---------------------------------------------------------------------------
# filter_gate2_candidates
# ---------------------------------------------------------------------------

def test_filter_gate2_requires_confidence_gt_085(gate_catalogue):
    """Gate 2 requires pc_confidence > 0.85 (stricter than Gate 1)."""
    result = filter_gate2_candidates(gate_catalogue)
    # TIC 1: SDE=8.5, conf=0.92 -> passes
    # TIC 4: SDE=7.0, conf=0.71 -> excluded (conf too low)
    # TIC 2: SDE=6.0 -> excluded (SDE too low)
    assert 1 in result["tic_id"].values
    assert 4 not in result["tic_id"].values
    assert 2 not in result["tic_id"].values


def test_filter_gate2_ranked_by_score(gate_catalogue):
    """Gate 2 candidates ranked by SDE * pc_confidence descending."""
    # Add more candidates to test ranking
    df = pd.DataFrame({
        "tic_id": [10, 11, 12],
        "tls_sde": [15.0, 7.5, 8.0],
        "pc_confidence": [0.90, 0.95, 0.86],
        "sector": [1, 1, 1],
    })
    result = filter_gate2_candidates(df, top_n=3)
    expected_order = [
        (15.0 * 0.90),  # TIC 10 = 13.5
        (7.5 * 0.95),   # TIC 11 = 7.125
        (8.0 * 0.86),   # TIC 12 = 6.88
    ]
    assert result["tic_id"].iloc[0] == 10   # highest
    assert result["tic_id"].iloc[1] == 11
    assert result["tic_id"].iloc[2] == 12   # lowest


def test_filter_gate2_top_n_limit(gate_catalogue):
    """top_n parameter limits number of returned candidates."""
    # Create many passing candidates
    df = pd.DataFrame({
        "tic_id": list(range(20)),
        "tls_sde": [10.0 + i for i in range(20)],
        "pc_confidence": [0.86] * 20,
        "sector": [1] * 20,
    })
    result = filter_gate2_candidates(df, top_n=5)
    assert len(result) == 5


# ---------------------------------------------------------------------------
# append_to_parquet
# ---------------------------------------------------------------------------

def test_append_to_parquet_adds_new_columns(tmp_path):
    """Appends new column values for a single TIC ID to Parquet."""
    catalogue_path = tmp_path / "master.parquet"
    df_orig = pd.DataFrame({
        "tic_id": [100, 200],
        "sector": [1, 1],
        "tls_period": [3.5, 7.2],
    })
    df_orig.to_parquet(catalogue_path, index=False)

    append_to_parquet(str(catalogue_path), 100, {"mcmc_rp_rs": 0.085, "mcmc_status": "converged"})

    df_result = pd.read_parquet(catalogue_path)
    # TIC 100 gets the new values
    row = df_result[df_result["tic_id"] == 100].iloc[0]
    assert row["mcmc_rp_rs"] == 0.085
    assert row["mcmc_status"] == "converged"
    # TIC 200 gets NaN for the new columns
    assert np.isnan(df_result.loc[df_result["tic_id"] == 200, "mcmc_rp_rs"].iloc[0])


def test_append_to_parquet_overwrites_existing(tmp_path):
    """Re-appending to an existing column overwrites the value."""
    catalogue_path = tmp_path / "master.parquet"
    df_orig = pd.DataFrame({
        "tic_id": [100],
        "mcmc_rp_rs": [0.05],
    })
    df_orig.to_parquet(catalogue_path, index=False)

    append_to_parquet(str(catalogue_path), 100, {"mcmc_rp_rs": 0.12})

    df_result = pd.read_parquet(catalogue_path)
    assert df_result["mcmc_rp_rs"].iloc[0] == 0.12


# ---------------------------------------------------------------------------
# ensure_directories
# ---------------------------------------------------------------------------

def test_ensure_directories_creates_all_paths(tmp_path):
    """Creates all Phase 3 output directories under base_path."""
    ensure_directories(str(tmp_path))
    for d in ["data/mcmc", "data/validation", "data/verification/triceratops",
              "data/verification/sherlock", "data/completeness",
              "outputs/plots", "outputs/completeness"]:
        assert (tmp_path / d).is_dir()


def test_ensure_directories_idempotent(tmp_path):
    """Calling ensure_directories twice does not error."""
    ensure_directories(str(tmp_path))
    ensure_directories(str(tmp_path))  # should not raise


# ---------------------------------------------------------------------------
# load_phase_folded
# ---------------------------------------------------------------------------

def test_load_phase_folded_returns_dict(tmp_path):
    """load_phase_folded returns a dict with numpy arrays."""
    folded_dir = tmp_path / "data" / "folded"
    folded_dir.mkdir(parents=True)
    phase = np.linspace(-0.5, 0.5, 2001)
    flux = np.ones_like(phase) - 0.005
    np.savez(folded_dir / "TIC_100_folded.npz", phase_global=phase, flux_global=flux)

    result = load_phase_folded(100, str(folded_dir))
    assert isinstance(result, dict)
    assert "phase_global" in result
    assert "flux_global" in result
    assert len(result["phase_global"]) == 2001


def test_load_phase_folded_missing_file():
    """Returns None when .npz file does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_phase_folded(999, tmpdir)
        assert result is None


# ---------------------------------------------------------------------------
# log_jsonl
# ---------------------------------------------------------------------------

def test_log_jsonl_appends_entry(tmp_path):
    """Appends a JSON-lines entry to a log file."""
    log_path = tmp_path / "test.log"
    entry = {"step": "test", "tic_id": 100, "status": "OK"}
    log_jsonl(str(log_path), entry)

    assert log_path.exists()
    with open(log_path) as f:
        line = f.readline().strip()
    parsed = json.loads(line)
    assert parsed == entry


def test_log_jsonl_multiple_entries(tmp_path):
    """Multiple calls append multiple lines."""
    log_path = tmp_path / "test.log"
    log_jsonl(str(log_path), {"a": 1})
    log_jsonl(str(log_path), {"b": 2})
    log_jsonl(str(log_path), {"c": 3})

    with open(log_path) as f:
        lines = f.readlines()
    assert len(lines) == 3
    assert json.loads(lines[0]) == {"a": 1}
    assert json.loads(lines[2]) == {"c": 3}
