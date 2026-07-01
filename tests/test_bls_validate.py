"""Tests for DET-02: BLS validation of TLS candidates."""

import numpy as np
from pipeline.detect.bls_validate import validate_candidates


def test_bls_validate_set_consistency_flag():
    """BLS validation should set bls_consistent flag on each candidate."""
    np.random.seed(42)
    n = 2000
    time = np.linspace(0, 30, n)
    # Inject a transit at period 3.0 days
    period = 3.0
    duration = 0.15
    depth = 0.005
    t0 = 1.5
    flux = np.ones(n)
    for epoch in range(11):
        center = t0 + epoch * period
        in_transit = np.abs(time - center) < duration / 2
        flux[in_transit] -= depth
    flux += np.random.normal(0, 0.001, n)
    flux_err = np.full(n, 0.001)

    lc_data = {
        (1, 1): {
            "time": time,
            "flux": flux,
            "flux_err": flux_err,
        }
    }

    candidates = [
        {
            "tic_id": 1,
            "sector": 1,
            "period": period,
            "duration": duration,
            "depth": depth,
            "sde": 10.0,
        },
        {
            "tic_id": 2,  # no lc_data for this TIC
            "sector": 1,
            "period": 5.0,
            "duration": 0.1,
            "depth": 0.001,
            "sde": 6.0,
        },
    ]

    validated = validate_candidates(candidates, lc_data)

    # Both candidates should have bls_consistent flag set
    assert "bls_consistent" in validated[0]
    assert "bls_consistent" in validated[1]
    # Candidate 2 has no lc_data → should be False
    assert validated[1]["bls_consistent"] is False


def test_bls_validate_handles_empty_candidates():
    """Empty candidate list should be returned unchanged."""
    result = validate_candidates([], {})
    assert result == []


def test_bls_validate_short_light_curve():
    """Light curves with < 100 points should get bls_consistent=False."""
    time = np.linspace(0, 1, 50)
    flux = np.ones(50)
    flux_err = np.full(50, 0.001)

    lc_data = {(1, 1): {"time": time, "flux": flux, "flux_err": flux_err}}
    candidates = [
        {"tic_id": 1, "sector": 1, "period": 2.0, "duration": 0.1, "depth": 0.001, "sde": 7.0}
    ]

    validated = validate_candidates(candidates, lc_data)
    assert validated[0]["bls_consistent"] is False


def test_bls_validate_gap_masked_data():
    """BLS should handle gap_mask in lc_data gracefully."""
    np.random.seed(42)
    n = 500
    time = np.linspace(0, 27, n)
    flux = np.ones(n)
    flux_err = np.full(n, 0.001)

    # Create lc_data with a gap_mask that masks out most points
    gap_mask = np.zeros(n, dtype=bool)
    gap_mask[10:] = True  # mask all but first 10

    lc_data = {(1, 1): {"time": time, "flux": flux, "flux_err": flux_err, "gap_mask": gap_mask}}
    candidates = [
        {"tic_id": 1, "sector": 1, "period": 3.0, "duration": 0.1, "depth": 0.001, "sde": 8.0}
    ]

    validated = validate_candidates(candidates, lc_data)
    # After masking, < 100 points → should be False
    assert validated[0]["bls_consistent"] is False
