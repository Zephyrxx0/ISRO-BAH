"""Tests for diagnostic plot helper functions (VIS-01, VIS-02)."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.visualization.generate_diagnostics import (
    _compute_batman_model,
    _compute_transit_epochs,
    _load_candidate_data,
)


# ---------------------------------------------------------------------------
# _compute_batman_model
# ---------------------------------------------------------------------------

def test_compute_batman_model_has_transit_dip():
    """batman model shows flux dip at phase 0 (transit center)."""
    phase = np.linspace(-0.5, 0.5, 2001)
    params = {
        "rp": 0.1,
        "inc": 89.0,
        "a": 10.0,
        "t0": 0.0,
        "per": 2.0,
    }
    ld = [0.4, 0.2]

    model = _compute_batman_model(phase, params, ld)
    assert isinstance(model, np.ndarray)
    assert len(model) == len(phase)
    # Flux at transit center (phase=0) should be below 1.0
    center_idx = np.argmin(np.abs(phase))
    assert model[center_idx] < 0.995


def test_compute_batman_model_out_of_transit_is_one():
    """Flux far from transit center is ~1.0."""
    phase = np.linspace(-0.5, 0.5, 2001)
    params = {
        "rp": 0.1,
        "inc": 89.0,
        "a": 10.0,
        "t0": 0.0,
        "per": 2.0,
    }
    ld = [0.4, 0.2]

    model = _compute_batman_model(phase, params, ld)
    # Far from transit center, flux ~1.0
    far_idx = np.argmin(np.abs(phase - 0.4))
    assert np.abs(model[far_idx] - 1.0) < 0.001


def test_compute_batman_model_with_different_ld():
    """Different limb darkening coefficients produce different models."""
    phase = np.linspace(-0.5, 0.5, 2001)
    params = {
        "rp": 0.1,
        "inc": 89.0,
        "a": 10.0,
        "t0": 0.0,
        "per": 2.0,
    }

    model_a = _compute_batman_model(phase, params, [0.4, 0.2])
    model_b = _compute_batman_model(phase, params, [0.1, 0.1])
    # Different LD should produce different model shapes
    assert not np.allclose(model_a, model_b)


# ---------------------------------------------------------------------------
# _compute_transit_epochs
# ---------------------------------------------------------------------------

def test_compute_transit_epochs():
    """Returns epoch times within observation window."""
    time = np.linspace(1000.0, 1030.0, 3000)
    period = 3.0
    t0 = 1000.5

    epochs = _compute_transit_epochs(time, period, t0)
    assert len(epochs) > 0
    # All epochs should be within [time.min(), time.max()]
    assert np.all(epochs >= time.min())
    assert np.all(epochs <= time.max())


def test_compute_transit_epochs_correct_spacing():
    """Epochs are evenly spaced by the period."""
    time = np.linspace(0.0, 100.0, 1000)
    period = 10.0
    t0 = 5.0

    epochs = _compute_transit_epochs(time, period, t0)
    diffs = np.diff(epochs)
    assert np.allclose(diffs, period)

    # n_start = ceil((0 - 5) / 10) = ceil(-0.5) = 0 -> t0 + 0*10 = 5
    # n_end = floor((100 - 5) / 10) = floor(9.5) = 9 -> t0 + 9*10 = 95
    assert epochs[0] == 5.0
    assert epochs[-1] == 95.0


def test_compute_transit_epochs_no_epochs_in_window():
    """Returns empty array if no epochs fall within time range."""
    time = np.linspace(0.0, 1.0, 100)
    period = 100.0
    t0 = 50.0

    epochs = _compute_transit_epochs(time, period, t0)
    assert len(epochs) == 0


# ---------------------------------------------------------------------------
# _load_candidate_data
# ---------------------------------------------------------------------------

@pytest.fixture
def diagnostics_fs(tmp_path):
    """Set up a synthetic filesystem for _load_candidate_data tests."""
    # Preprocessed LC
    prep_dir = tmp_path / "preprocessed" / "sector1"
    prep_dir.mkdir(parents=True)
    prep_time = np.linspace(1000, 1030, 3000)
    prep_flux = np.ones(3000)
    np.savez(
        prep_dir / "TIC_999_preprocessed.npz",
        time=prep_time, flux=prep_flux, flux_raw=prep_flux + 0.001,
    )

    # Folded LC
    folded_dir = tmp_path / "folded"
    folded_dir.mkdir(parents=True)
    phase = np.linspace(-0.5, 0.5, 2001)
    flux_folded = np.ones(2001)
    np.savez(
        folded_dir / "TIC_999_folded.npz",
        phase_global=phase, flux_global=flux_folded,
    )

    # MCMC dir (no posteriors/NM files yet — test fallback)
    mcmc_dir = tmp_path / "mcmc"
    mcmc_dir.mkdir(parents=True)

    return {
        "tmp_path": tmp_path,
        "prep_dir": str(prep_dir.parent),  # "preprocessed/"
        "folded_dir": str(folded_dir),
        "mcmc_dir": str(mcmc_dir),
    }


def test_load_candidate_data_returns_expected_keys(diagnostics_fs):
    """_load_candidate_data returns dict with all required keys."""
    row = pd.Series({
        "sector": 1,
        "tls_period": 3.0,
        "tls_t0": 10005.0,
        "tls_sde": 10.0,
        "classification": "PC",
        "pc_confidence": 0.95,
        "prob_pc": 0.85, "prob_eb": 0.05, "prob_blend": 0.05, "prob_sv": 0.05,
        "ld_u1": 0.4, "ld_u2": 0.2,
    })

    data = _load_candidate_data(
        999, row,
        diagnostics_fs["prep_dir"],
        diagnostics_fs["folded_dir"],
        diagnostics_fs["mcmc_dir"],
    )

    assert data is not None
    assert "time" in data
    assert "flux_detrended" in data
    assert "phase_global" in data
    assert "flux_global" in data
    assert "tls_period" in data
    assert data["tls_period"] == 3.0
    assert data["softmax_probs"] == [0.85, 0.05, 0.05, 0.05]
    assert data["model_source"] == "none"  # no NM or MCMC files present


def test_load_candidate_data_missing_preprocessed():
    """Returns None when preprocessed LC is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        folded_dir = Path(tmpdir) / "folded"
        folded_dir.mkdir(parents=True)
        np.savez(folded_dir / "TIC_999_folded.npz",
                 phase_global=np.linspace(-0.5, 0.5, 100), flux_global=np.ones(100))

        row = pd.Series({
            "sector": 1, "tls_period": 3.0, "tls_t0": 1000.0,
            "tls_sde": 8.0, "classification": "PC", "pc_confidence": 0.9,
            "prob_pc": 0.8, "prob_eb": 0.1, "prob_blend": 0.05, "prob_sv": 0.05,
            "ld_u1": 0.4, "ld_u2": 0.2,
        })

        data = _load_candidate_data(999, row, str(tmpdir), str(folded_dir), str(tmpdir))
        assert data is None


def test_load_candidate_data_missing_folded(diagnostics_fs):
    """Returns None when phase-folded .npz is missing."""
    row = pd.Series({
        "sector": 1, "tls_period": 3.0, "tls_t0": 1000.0,
        "tls_sde": 8.0, "classification": "PC", "pc_confidence": 0.9,
        "prob_pc": 0.8, "prob_eb": 0.1, "prob_blend": 0.05, "prob_sv": 0.05,
        "ld_u1": 0.4, "ld_u2": 0.2,
    })

    # Point to a non-existent folded dir
    data = _load_candidate_data(
        999, row,
        diagnostics_fs["prep_dir"],
        str(diagnostics_fs["tmp_path"] / "nonexistent"),
        diagnostics_fs["mcmc_dir"],
    )
    assert data is None


def test_load_candidate_data_with_nelder_mead(diagnostics_fs):
    """When MCMC not present but NM file exists, model_source='nelder_mead'."""
    # Create Nelder-Mead result
    tic_dir = Path(diagnostics_fs["mcmc_dir"]) / "999"
    tic_dir.mkdir(parents=True)
    with open(tic_dir / "nelder_mead.json", "w") as f:
        json.dump({
            "nm_rp_rs": 0.08, "nm_inclination": 89.5,
            "nm_a_rs": 12.0, "nm_t0": 0.0, "nm_period": 3.0,
            "nm_chi2": 1.2,
        }, f)

    row = pd.Series({
        "sector": 1, "tls_period": 3.0, "tls_t0": 1000.0,
        "tls_sde": 10.0, "classification": "PC", "pc_confidence": 0.95,
        "prob_pc": 0.9, "prob_eb": 0.05, "prob_blend": 0.03, "prob_sv": 0.02,
        "ld_u1": 0.4, "ld_u2": 0.2,
    })

    data = _load_candidate_data(
        999, row,
        diagnostics_fs["prep_dir"],
        diagnostics_fs["folded_dir"],
        diagnostics_fs["mcmc_dir"],
    )

    assert data is not None
    assert data["model_source"] == "nelder_mead"
    assert data["model_params"]["rp"] == 0.08
    assert data["model_params"]["per"] == 3.0
