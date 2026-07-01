"""Tests for PREP-06: star exclusion filters."""

import math
from pipeline.preprocess.filters import get_exclusion_reason, should_process


def test_saturated_star_excluded_for_bright_magnitude():
    """Stars with Tmag < 6 should be excluded as SATURATED."""
    assert get_exclusion_reason(5.0, 1000) == "SATURATED"
    assert get_exclusion_reason(5.9, 1000) == "SATURATED"


def test_too_few_cadences_excluded():
    """Light curves with fewer than 500 valid cadences should be excluded."""
    assert get_exclusion_reason(10.0, 499) == "TOO_FEW_CADENCES"
    assert get_exclusion_reason(10.0, 0) == "TOO_FEW_CADENCES"


def test_valid_star_passes_all_filters():
    """Stars with Tmag >= 6 and >= 500 cadences should return NONE."""
    assert get_exclusion_reason(10.0, 500) == "NONE"
    assert get_exclusion_reason(6.0, 500) == "NONE"
    assert get_exclusion_reason(15.0, 2000) == "NONE"


def test_none_tmag_handled_gracefully():
    """None tmag should not trigger SATURATED (only non-None values checked)."""
    assert get_exclusion_reason(None, 1000) == "NONE"


def test_nan_tmag_handled_gracefully():
    """NaN tmag should not trigger SATURATED."""
    assert get_exclusion_reason(float("nan"), 1000) == "NONE"


def test_saturated_priority_over_too_few_cadences():
    """SATURATED should take priority when both conditions are met."""
    result = get_exclusion_reason(5.5, 100)
    # Saturated check comes first in implementation
    assert result == "SATURATED"


def test_should_process_returns_true_for_clean_star():
    """should_process returns True when get_exclusion_reason returns NONE."""
    assert should_process(10.0, 1000) is True


def test_should_process_returns_false_for_saturated():
    """should_process returns False for saturated stars."""
    assert should_process(5.0, 1000) is False


def test_should_process_returns_false_for_too_few_cadences():
    """should_process returns False for insufficient cadences."""
    assert should_process(10.0, 100) is False
