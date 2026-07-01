"""Tests for Gate 1 Nelder-Mead batman fitting."""

import numpy as np
import pandas as pd
import pytest

from src.characterization.nelder_mead_fit import fit_single_candidate


@pytest.fixture
def mock_catalogue(tmp_path):
    """Create minimal catalogue with one candidate."""
    df = pd.DataFrame({
        "tic_id": [12345],
        "tls_period": [2.0],
        "tls_t0": [0.0],
        "tls_depth": [0.01],  # 1% depth -> rp/rs ~ 0.1
        "tls_sde": [10.0],
        "pc_confidence": [0.92],
        "stellar_mass": [1.0],
        "stellar_radius": [1.0],
        "ld_u1": [0.4],
        "ld_u2": [0.2],
    })
    return df


@pytest.fixture
def mock_folded_data(tmp_path):
    """Create synthetic phase-folded light curve with transit."""
    import batman

    phase = np.linspace(-0.5, 0.5, 2001)
    params = batman.TransitParams()
    params.t0 = 0.0
    params.per = 2.0
    params.rp = 0.1
    params.a = 10.0
    params.inc = 89.0
    params.ecc = 0.0
    params.w = 90.0
    params.u = [0.4, 0.2]
    params.limb_dark = "quadratic"

    t = phase * params.per
    m = batman.TransitModel(params, t)
    flux = m.light_curve(params)
    flux += np.random.normal(0, 0.0002, len(flux))

    folded_dir = tmp_path / "data" / "folded"
    folded_dir.mkdir(parents=True)
    np.savez(
        folded_dir / "TIC_12345_folded.npz",
        phase_global=phase,
        flux_global=flux,
    )
    return str(folded_dir)


def test_fit_recovers_known_transit(mock_catalogue, mock_folded_data):
    """Nelder-Mead recovers injected transit params within 10%."""
    row = mock_catalogue.iloc[0]
    result = fit_single_candidate(12345, row, mock_catalogue, mock_folded_data)

    assert result is not None
    assert abs(result["nm_rp_rs"] - 0.1) / 0.1 < 0.10  # within 10%
    assert result["nm_chi2"] < 5.0  # reasonable fit
    assert result["nm_period"] == 2.0  # period fixed
