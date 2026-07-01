"""Tests for SHERLOCK output parsing logic (VAL-05)."""

import pytest

from src.characterization.sherlock_runner import _parse_sherlock_output


def test_parse_best_period_line():
    """Parses a line containing 'best' and 'period' with a valid period value."""
    stdout = (
        "Loading data...\n"
        "Running BLS...\n"
        "best period = 3.5241\n"
        "Done.\n"
    )
    result = _parse_sherlock_output(100, stdout)
    assert result == pytest.approx(3.5241)


def test_parse_period_within_valid_range():
    """Returns period when value is between 0.5 and 30.0 days."""
    stdout = "best-fit period: 12.75 days"
    result = _parse_sherlock_output(200, stdout)
    assert result == pytest.approx(12.75)


def test_parse_period_at_min_boundary():
    """Returns period when exactly at minimum boundary (0.5 days)."""
    stdout = "best period: 0.5"
    result = _parse_sherlock_output(300, stdout)
    assert result == pytest.approx(0.5)


def test_parse_period_at_max_boundary():
    """Returns period when exactly at maximum boundary (30.0 days)."""
    stdout = "best period: 30.0"
    result = _parse_sherlock_output(400, stdout)
    assert result == pytest.approx(30.0)


def test_parse_period_below_range_ignored():
    """Period < 0.5 days is ignored (not in valid range)."""
    stdout = "best period: 0.3"
    result = _parse_sherlock_output(500, stdout)
    assert result is None


def test_parse_period_above_range_ignored():
    """Period > 30.0 days is ignored (not in valid range)."""
    stdout = "best period: 45.0"
    result = _parse_sherlock_output(600, stdout)
    assert result is None


def test_parse_no_period_line():
    """Returns None when stdout contains no period marker."""
    stdout = "Loading...\nError: no transit detected\nDone."
    result = _parse_sherlock_output(700, stdout)
    assert result is None


def test_parse_empty_stdout():
    """Returns None for empty output."""
    result = _parse_sherlock_output(800, "")
    assert result is None


def test_parse_partial_match_no_best():
    """'period' without 'best' in the same line is not matched."""
    stdout = "Detected period: 5.2 days"
    result = _parse_sherlock_output(900, stdout)
    assert result is None


def test_parse_negative_number_ignored():
    """Negative numbers are not valid period values."""
    stdout = "best period: -2.5"
    result = _parse_sherlock_output(1000, stdout)
    assert result is None
