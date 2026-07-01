"""Tests for TRICERATOPS+ FPP classification logic (VAL-04)."""

import pytest

from src.characterization.triceratops_runner import _classify_fpp


def test_classify_validated_planet():
    """FPP < 0.015 and NFPP < 0.001 -> VALIDATED."""
    assert _classify_fpp(0.01, 0.0005) == "VALIDATED"


def test_classify_validated_boundary_fpp():
    """FPP just below 0.015 threshold is VALIDATED."""
    assert _classify_fpp(0.01499, 0.0005) == "VALIDATED"


def test_classify_likely_planet():
    """FPP < 0.5 and NFPP < 0.001 but not validated -> LIKELY_PLANET."""
    assert _classify_fpp(0.3, 0.0005) == "LIKELY_PLANET"


def test_classify_likely_planet_boundary():
    """FPP just below 0.5 is LIKELY_PLANET (not validated if FPP >= 0.015)."""
    assert _classify_fpp(0.499, 0.0005) == "LIKELY_PLANET"


def test_classify_likely_planet_min_fpp_for_non_validated():
    """FPP = 0.015 exactly is LIKELY_PLANET (not < 0.015, so not VALIDATED)."""
    assert _classify_fpp(0.015, 0.0005) == "LIKELY_PLANET"


def test_classify_likely_nearby_fp():
    """NFPP > 0.1 -> LIKELY_NEARBY_FP regardless of FPP."""
    assert _classify_fpp(0.01, 0.15) == "LIKELY_NEARBY_FP"


def test_classify_likely_nearby_fp_boundary():
    """NFPP exactly at 0.1 does NOT trigger (must be > 0.1)."""
    result = _classify_fpp(0.01, 0.1)
    # 0.1 is not > 0.1, so falls through
    assert result != "LIKELY_NEARBY_FP"


def test_classify_inconclusive():
    """Moderate FPP with low NFPP that doesn't meet validated/likely thresholds."""
    assert _classify_fpp(0.6, 0.0005) == "INCONCLUSIVE"


def test_classify_inconclusive_with_high_nfpp():
    """When NFPP between 0.001 and 0.1 and FPP high, INCONCLUSIVE."""
    assert _classify_fpp(0.4, 0.05) == "INCONCLUSIVE"


def test_classify_failed_fpp_none():
    """None FPP returns FAILED."""
    assert _classify_fpp(None, 0.001) == "FAILED"


def test_classify_failed_nfpp_none():
    """None NFPP returns FAILED."""
    assert _classify_fpp(0.01, None) == "FAILED"


def test_classify_failed_both_none():
    """Both None returns FAILED."""
    assert _classify_fpp(None, None) == "FAILED"


def test_classify_validated_both_at_zero():
    """FPP=0, NFPP=0 -> both < thresholds, VALIDATED."""
    assert _classify_fpp(0.0, 0.0) == "VALIDATED"


def test_classify_fpp_at_exactly_05_is_not_likely():
    """FPP = 0.5 exactly is not < 0.5, so skips LIKELY_PLANET."""
    # FPP=0.5, NFPP=0.0005: not VALIDATED (FPP >= 0.015), not LIKELY_PLANET (FPP not < 0.5)
    # NFPP not > 0.1, so falls through to INCONCLUSIVE
    assert _classify_fpp(0.5, 0.0005) == "INCONCLUSIVE"
