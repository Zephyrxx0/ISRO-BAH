"""Tests for DET-05: 3-tier SDE gating."""

import pandas as pd
from pathlib import Path
from pipeline.detect.sde_gate import apply_sde_gating, save_tls_results


def test_sde_gating_assigns_full_pipeline_for_high_sde(sample_candidates):
    """Candidates with SDE >= 7 should get FULL_PIPELINE disposition."""
    df = apply_sde_gating(sample_candidates)
    high = df[df["sde"] >= 7.0]
    assert len(high) > 0
    assert all(high["disposition"] == "FULL_PIPELINE")


def test_sde_gating_assigns_sub_threshold_for_mid_sde(sample_candidates):
    """Candidates with 5 <= SDE < 7 should get SUB_THRESHOLD disposition."""
    df = apply_sde_gating(sample_candidates)
    mid = df[(df["sde"] >= 5.0) & (df["sde"] < 7.0)]
    assert len(mid) > 0
    assert all(mid["disposition"] == "SUB_THRESHOLD")


def test_sde_gating_assigns_discard_for_low_sde(sample_candidates):
    """Candidates with SDE < 5 should get DISCARD disposition."""
    df = apply_sde_gating(sample_candidates)
    low = df[df["sde"] < 5.0]
    assert len(low) > 0
    assert all(low["disposition"] == "DISCARD")


def test_sde_gating_adds_bls_consistent_column():
    """apply_sde_gating should ensure bls_consistent column exists."""
    df = apply_sde_gating([{
        "tic_id": 100, "sector": 1, "planet_num": 1,
        "period": 3.0, "t0": 2458000.0, "duration": 0.1, "depth": 0.001,
        "sde": 8.0, "snr": 10.0, "cdpp": 30.0, "chi2": 1.0, "chi2_red": 1.0,
    }])
    assert "bls_consistent" in df.columns
    assert bool(df["bls_consistent"].iloc[0]) is False


def test_sde_gating_sorts_by_sde_descending(sample_candidates):
    """Results should be sorted by SDE descending."""
    df = apply_sde_gating(sample_candidates)
    sde_values = df["sde"].values
    for i in range(len(sde_values) - 1):
        assert sde_values[i] >= sde_values[i + 1]


def test_sde_gating_empty_input():
    """Empty input should return empty DataFrame with expected columns."""
    df = apply_sde_gating([])
    assert len(df) == 0
    assert "disposition" in df.columns
    assert "bls_consistent" in df.columns


def test_sde_gating_returns_dataframe():
    """apply_sde_gating should always return a pandas DataFrame."""
    df = apply_sde_gating([])
    assert isinstance(df, pd.DataFrame)


def test_save_tls_results_creates_parquet(tmp_path, monkeypatch):
    """save_tls_results should write a parquet file."""
    import pipeline.config as cfg
    monkeypatch.setattr(cfg, "TLS_RESULTS_PATH", str(tmp_path / "tls_candidates.parquet"))

    df = pd.DataFrame([{"tic_id": 1, "sde": 10.0, "disposition": "FULL_PIPELINE"}])
    path = save_tls_results(df)

    assert path.exists()
    assert path.suffix == ".parquet"

    # Verify roundtrip
    loaded = pd.read_parquet(path)
    assert loaded["tic_id"].iloc[0] == 1
