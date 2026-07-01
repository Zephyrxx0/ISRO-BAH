"""Tests for validation parameter recovery logic."""

import pytest

from src.validation.validate import validate_parameter_recovery


def test_pass_within_tolerance():
    """Recovery within all tolerances returns overall_pass=True."""
    recovered = {"period": 1.2749250, "depth_ppm": 14800.0, "duration_days": 0.1195}
    published = {"period": 1.2749255, "depth_ppm": 14840.0, "duration_days": 0.1203}
    result = validate_parameter_recovery(recovered, published)

    assert result["overall_pass"] is True
    assert result["period"]["pass"] is True
    assert result["depth_ppm"]["pass"] is True
    assert result["duration_days"]["pass"] is True


def test_fail_period_outside_tolerance():
    """Period error > 0.1% returns period pass=False."""
    recovered = {"period": 1.2800, "depth_ppm": 14840.0, "duration_days": 0.1203}
    published = {"period": 1.2749255, "depth_ppm": 14840.0, "duration_days": 0.1203}
    result = validate_parameter_recovery(recovered, published)

    assert result["period"]["pass"] is False
    assert result["overall_pass"] is False


def test_fail_depth_outside_tolerance():
    """Depth error > 5% returns depth pass=False."""
    recovered = {"period": 1.2749255, "depth_ppm": 16000.0, "duration_days": 0.1203}
    published = {"period": 1.2749255, "depth_ppm": 14840.0, "duration_days": 0.1203}
    result = validate_parameter_recovery(recovered, published)

    assert result["depth_ppm"]["pass"] is False
    assert result["depth_ppm"]["error_pct"] > 5.0
