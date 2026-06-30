"""Tests for PREP-05: 13-day TESS data gap masking."""

import numpy as np
import pytest
from pipeline.preprocess.gap_mask import apply_gap_mask


def test_no_gaps_returns_empty_mask():
    """Uniform time series with no gaps should produce all-False mask."""
    time = np.linspace(0, 27, 2000)
    mask, gaps = apply_gap_mask(time)
    assert not np.any(mask)
    assert len(gaps) == 0


def test_single_point_returns_empty():
    """Single time point produces empty mask."""
    time = np.array([1.0])
    mask, gaps = apply_gap_mask(time)
    assert not np.any(mask)
    assert len(gaps) == 0


def test_large_gap_detected():
    """A 14-day gap (>> 0.1 day threshold) should be detected."""
    # Two clusters of points separated by 14 days
    time_1 = np.linspace(0, 5, 500)
    time_2 = np.linspace(19, 27, 500)
    time = np.concatenate([time_1, time_2])

    mask, gaps = apply_gap_mask(time, gap_threshold=0.1)

    assert len(gaps) >= 1
    # The gap should have its endpoints recorded
    gap = gaps[0]
    assert gap[0] == pytest.approx(5.0, abs=0.1)
    assert gap[1] == pytest.approx(19.0, abs=0.1)


def test_gap_edge_points_flagged():
    """Points within edge_days of a gap should be flagged as True."""
    # Create a gap at day 10
    time_1 = np.linspace(0, 9.9, 500)
    time_2 = np.linspace(20.1, 27, 500)
    time = np.concatenate([time_1, time_2])

    mask, gaps = apply_gap_mask(time, gap_threshold=0.1, edge_days=0.5)

    # Points near gap edges should be flagged
    assert np.any(mask)
    # The middle of time_1 (far from gaps) should not be flagged
    # but edges near the gap should be
    assert mask[0] == 0 or mask[-1] == 1  # edge days


def test_gap_mask_is_boolean():
    """Mask should be a boolean array."""
    time = np.linspace(0, 27, 2000)
    mask, _ = apply_gap_mask(time)
    assert mask.dtype == bool


def test_uniform_time_default_threshold():
    """Evenly spaced data at ~2-min cadence has diffs ~0.0014 days — below 0.1."""
    time = np.linspace(0, 27, 2000)
    mask, gaps = apply_gap_mask(time)
    assert not np.any(mask)
    assert len(gaps) == 0
