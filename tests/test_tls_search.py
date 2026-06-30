"""Tests for DET-01, DET-03, DET-04: TLS period search with multi-planet iteration.

These tests use synthetic transit injection. The TLS search should recover
the injected period, duration, and depth within tolerance.
"""

import numpy as np
import tempfile
import pytest
from pathlib import Path
from pipeline.detect.tls_search import run_tls_single


@pytest.mark.slow
def test_run_tls_single_recovers_injected_period(monkeypatch):
    """TLS should recover the period of a strong injected transit within 5%."""
    np.random.seed(42)

    n = 3000
    time = np.linspace(0, 30, n)
    flux = np.ones(n)
    period = 3.0
    duration = 0.15
    depth = 0.01
    t0 = 1.5

    for epoch in range(int(time[-1] / period) + 1):
        center = t0 + epoch * period
        in_transit = np.abs(time - center) < duration / 2
        flux[in_transit] -= depth

    flux += np.random.normal(0, 0.0005, n)
    flux_err = np.full(n, 0.0005)

    with tempfile.TemporaryDirectory() as tmpdir:
        import pipeline.config as cfg
        monkeypatch.setattr(cfg, "PREP_DIR", Path(tmpdir) / "preprocessed")
        monkeypatch.setattr(cfg, "RAW_DIR", Path(tmpdir) / "raw")

        prep_dir = Path(tmpdir) / "preprocessed"
        prep_dir.mkdir(parents=True, exist_ok=True)
        path = prep_dir / f"tic0000000000000001_s0001_preprocessed.npz"
        import json
        np.savez_compressed(
            str(path),
            time=time,
            flux=flux,
            flux_err=flux_err,
            meta_json=json.dumps({"tic_id": 1, "sector": 1}),
        )

        results = run_tls_single((1, 1, 0.3, 0.3))

        assert len(results) >= 1, "TLS should find at least one transit signal"
        best = results[0]
        assert abs(best["period"] - period) / period < 0.05, (
            f"Period recovery: got {best['period']:.3f}, expected {period:.3f}"
        )
        assert best["sde"] > 5.0, f"SDE too low: {best['sde']}"
        assert best["snr"] > 5.0, f"SNR too low: {best['snr']}"


@pytest.mark.slow
def test_run_tls_single_returns_expected_keys(monkeypatch):
    """TLS results should contain all expected keys."""
    np.random.seed(42)

    n = 2000
    time = np.linspace(0, 27, n)
    flux = np.ones(n)
    period = 2.5
    duration = 0.1
    depth = 0.008
    t0 = 1.0

    for epoch in range(int(time[-1] / period) + 1):
        center = t0 + epoch * period
        in_transit = np.abs(time - center) < duration / 2
        flux[in_transit] -= depth

    flux += np.random.normal(0, 0.0005, n)
    flux_err = np.full(n, 0.0005)

    with tempfile.TemporaryDirectory() as tmpdir:
        import pipeline.config as cfg
        monkeypatch.setattr(cfg, "PREP_DIR", Path(tmpdir) / "preprocessed")
        monkeypatch.setattr(cfg, "RAW_DIR", Path(tmpdir) / "raw")

        prep_dir = Path(tmpdir) / "preprocessed"
        prep_dir.mkdir(parents=True, exist_ok=True)
        path = prep_dir / f"tic0000000000000042_s0001_preprocessed.npz"
        import json
        np.savez_compressed(
            str(path),
            time=time,
            flux=flux,
            flux_err=flux_err,
            meta_json=json.dumps({"tic_id": 42, "sector": 1}),
        )

        results = run_tls_single((42, 1, 0.3, 0.3))

        assert len(results) >= 1
        r = results[0]
        required_keys = ["tic_id", "sector", "planet_num", "period", "t0",
                         "duration", "depth", "sde", "snr", "cdpp"]
        for key in required_keys:
            assert key in r, f"Missing key: {key}"
        assert r["tic_id"] == 42


def test_run_tls_single_short_data_returns_empty(monkeypatch):
    """TLS should return empty results for < 100 data points."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import pipeline.config as cfg
        monkeypatch.setattr(cfg, "PREP_DIR", Path(tmpdir) / "preprocessed")
        monkeypatch.setattr(cfg, "RAW_DIR", Path(tmpdir) / "raw")

        prep_dir = Path(tmpdir) / "preprocessed"
        prep_dir.mkdir(parents=True, exist_ok=True)

        time = np.linspace(0, 1, 50)
        flux = np.ones(50)
        flux_err = np.full(50, 0.001)

        path = prep_dir / f"tic0000000000000002_s0001_preprocessed.npz"
        import json
        np.savez_compressed(
            str(path),
            time=time,
            flux=flux,
            flux_err=flux_err,
            meta_json=json.dumps({"tic_id": 2, "sector": 1}),
        )

        results = run_tls_single((2, 1, 0.3, 0.3))
        assert len(results) == 0, "Short light curves should yield no TLS results"


@pytest.mark.slow
def test_tls_handles_gap_mask(monkeypatch):
    """TLS should exclude gap-masked points from period search."""
    np.random.seed(42)

    n = 2000
    time = np.linspace(0, 27, n)
    flux = np.ones(n)
    period = 3.0
    duration = 0.15
    depth = 0.01
    t0 = 1.5

    for epoch in range(9):
        center = t0 + epoch * period
        in_transit = np.abs(time - center) < duration / 2
        flux[in_transit] -= depth

    flux += np.random.normal(0, 0.0005, n)
    flux_err = np.full(n, 0.0005)

    gap_mask = np.zeros(n, dtype=bool)
    gap_mask[0:10] = True

    with tempfile.TemporaryDirectory() as tmpdir:
        import pipeline.config as cfg
        monkeypatch.setattr(cfg, "PREP_DIR", Path(tmpdir) / "preprocessed")
        monkeypatch.setattr(cfg, "RAW_DIR", Path(tmpdir) / "raw")

        prep_dir = Path(tmpdir) / "preprocessed"
        prep_dir.mkdir(parents=True, exist_ok=True)
        path = prep_dir / f"tic0000000000000003_s0001_preprocessed.npz"
        import json
        np.savez_compressed(
            str(path),
            time=time,
            flux=flux,
            flux_err=flux_err,
            gap_mask=gap_mask,
            meta_json=json.dumps({"tic_id": 3, "sector": 1}),
        )

        results = run_tls_single((3, 1, 0.3, 0.3))
        assert len(results) >= 1, "TLS should detect transit despite gap mask"
        assert abs(results[0]["period"] - period) / period < 0.05
