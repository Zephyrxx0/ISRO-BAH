"""Shared test fixtures for Phase 1 validation tests."""

import numpy as np
import pandas as pd
import tempfile
import pytest
from pathlib import Path


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")


@pytest.fixture
def synthetic_time_series():
    """Generate a realistic synthetic TESS-like time series.

    Returns dict with time, flux, flux_err, and quality arrays.
    ~1800 points over 27 days at 2-min cadence (TESS sector).
    """
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 27, n)  # ~27 days, 2-min cadence
    # Baseline flux ~1.0 with Gaussian noise
    flux = 1.0 + np.random.normal(0, 0.001, n)
    flux_err = np.full(n, 0.0005) * 1.5  # typical TESS errors
    quality = np.zeros(n, dtype=np.int32)
    return {"time": time, "flux": flux, "flux_err": flux_err, "quality": quality}


@pytest.fixture
def synthetic_flat_time_series():
    """Flat time series with no trends - for sigma clipping tests."""
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 27, n)
    flux = 1.0 + np.random.normal(0, 0.0005, n)
    flux_err = np.full(n, 0.0005)
    return {"time": time, "flux": flux, "flux_err": flux_err}


@pytest.fixture
def synthetic_transit():
    """Synthetic time series with a box-shaped transit signal.

    Injects a ~500 ppm transit at period 3 days, duration 3 hours.
    Returns dict with time, flux, flux_err and transit parameters.
    """
    np.random.seed(42)
    n = 3000
    time = np.linspace(0, 30, n)
    flux = np.ones(n)
    # Inject transits at period 3.0 days
    period = 3.0
    duration = 0.125  # 3 hours in days
    depth = 0.0005  # 500 ppm
    t0 = 1.5  # first transit center

    for epoch in range(int(time[-1] / period) + 1):
        center = t0 + epoch * period
        in_transit = np.abs(time - center) < duration / 2
        flux[in_transit] -= depth

    # Add noise
    flux += np.random.normal(0, 0.0002, n)
    flux_err = np.full(n, 0.0005)
    return {
        "time": time,
        "flux": flux,
        "flux_err": flux_err,
        "period": period,
        "duration": duration,
        "depth": depth,
        "t0": t0,
    }


@pytest.fixture
def tmp_npz_dir():
    """Temporary directory for npz file roundtrip tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_ld_parquet():
    """Create a small limb darkening parquet table for testing."""
    df = pd.DataFrame(
        {
            "teff": [3000.0, 4000.0, 5000.0, 6000.0, 7000.0],
            "u1": [0.35, 0.30, 0.25, 0.20, 0.15],
            "u2": [0.25, 0.22, 0.20, 0.15, 0.10],
        }
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "claret_ld.parquet"
        df.to_parquet(path)
        yield path


@pytest.fixture
def sample_candidates():
    """Sample TLS candidate dicts for SDE gating tests."""
    return [
        {
            "tic_id": 100,
            "sector": 1,
            "planet_num": 1,
            "period": 3.5,
            "t0": 2458000.0,
            "duration": 0.15,
            "depth": 0.0005,
            "sde": 8.5,
            "snr": 12.0,
            "cdpp": 30.0,
            "chi2": 1.2,
            "chi2_red": 1.1,
        },
        {
            "tic_id": 100,
            "sector": 1,
            "planet_num": 2,
            "period": 7.2,
            "t0": 2458002.0,
            "duration": 0.20,
            "depth": 0.0003,
            "sde": 6.0,
            "snr": 8.0,
            "cdpp": 30.0,
            "chi2": 1.5,
            "chi2_red": 1.4,
        },
        {
            "tic_id": 200,
            "sector": 1,
            "planet_num": 1,
            "period": 1.2,
            "t0": 2458001.0,
            "duration": 0.08,
            "depth": 0.0002,
            "sde": 3.5,
            "snr": 4.0,
            "cdpp": 45.0,
            "chi2": 0.9,
            "chi2_red": 0.8,
        },
    ]


@pytest.fixture
def sample_tls_result():
    """Single TLS result dict for transit injection test verification."""
    return {
        "tic_id": 999,
        "sector": 1,
        "period": 3.0,
        "t0": 2458001.5,
        "duration": 0.125,
        "depth": 0.0005,
        "sde": 10.0,
        "snr": 15.0,
        "cdpp": 25.0,
        "chi2": 1.1,
        "chi2_red": 1.0,
    }
