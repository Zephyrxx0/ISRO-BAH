"""Tests for Gate 2 emcee MCMC sampler."""

import json

import numpy as np
import pandas as pd
import pytest

from src.characterization.mcmc_sampler import (
    _compute_bounds,
    _extract_posteriors,
    run_mcmc_single,
)


def test_compute_bounds_from_nm():
    """Bounds are centered on NM result with correct ranges."""
    nm = {"nm_rp_rs": 0.1, "nm_inclination": 88.0, "nm_a_rs": 10.0,
          "nm_t0": 0.0, "nm_period": 2.0}
    tls_row = pd.Series({"tls_period": 2.0})
    bounds = _compute_bounds(nm, tls_row)

    assert bounds["rp_min"] < 0.1 < bounds["rp_max"]
    assert bounds["per_min"] == pytest.approx(2.0 * 0.999)
    assert bounds["per_max"] == pytest.approx(2.0 * 1.001)
    assert bounds["inc_max"] == 90.0


def test_extract_posteriors_shape():
    """Posteriors extraction produces expected keys."""
    fake_samples = np.random.randn(500, 5) * 0.01 + np.array([0.1, 88.0, 10.0, 0.0, 2.0])
    posteriors = _extract_posteriors(fake_samples)

    assert "mcmc_rp_rs" in posteriors
    assert "mcmc_rp_rs_err_low" in posteriors
    assert "mcmc_rp_rs_err_high" in posteriors
    assert "mcmc_period" in posteriors
    assert "mcmc_depth_ppm" in posteriors
    assert "mcmc_duration" in posteriors
    assert posteriors["mcmc_rp_rs"] == pytest.approx(0.1, abs=0.01)
