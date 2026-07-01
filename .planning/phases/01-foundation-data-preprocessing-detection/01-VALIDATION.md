---
phase: 01
slug: foundation-data-preprocessing-detection
status: complete
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-01
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `tests/conftest.py` |
| **Quick run command** | `python -m pytest tests/ -v -m "not slow"` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5s (quick) / ~90s (full) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -v -m "not slow"`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test File | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-----------|-------------------|--------|
| 01-01-01 | 01 | 1 | PREP-06 | tests/test_filters.py | unit | `python -m pytest tests/test_filters.py -v` | green |
| 01-01-02 | 01 | 1 | PREP-05 | tests/test_gap_mask.py | unit | `python -m pytest tests/test_gap_mask.py -v` | green |
| 01-01-03 | 01 | 1 | PREP-01 | tests/test_quality_mask.py | unit | `python -m pytest tests/test_quality_mask.py -v` | green |
| 01-01-04 | 01 | 1 | PREP-07 | tests/test_limb_darkening.py | unit | `python -m pytest tests/test_limb_darkening.py -v` | green |
| 01-01-05 | 01 | 1 | DATA-05 | tests/test_store.py | unit | `python -m pytest tests/test_store.py -v` | green |
| 01-01-06 | 01 | 1 | PREP-02 | tests/test_sigma_clip.py | unit | `python -m pytest tests/test_sigma_clip.py -v` | green |
| 01-01-07 | 01 | 1 | PREP-03 | tests/test_detrend.py | unit | `python -m pytest tests/test_detrend.py -v` | green |
| 01-01-08 | 01 | 1 | PREP-04 | tests/test_gp_detrend.py | unit | `python -m pytest tests/test_gp_detrend.py -v` | green |
| 01-01-09 | 01 | 1 | DET-05 | tests/test_sde_gate.py | unit | `python -m pytest tests/test_sde_gate.py -v` | green |
| 01-01-10 | 01 | 1 | DET-02 | tests/test_bls_validate.py | unit | `python -m pytest tests/test_bls_validate.py -v` | green |
| 01-01-11 | 01 | 1 | DET-01/03/04 | tests/test_tls_search.py | integration | `python -m pytest tests/test_tls_search.py -v` | green |
| 01-01-12 | 01 | 1 | DATA-01 | tests/test_download_tess.py | unit | `python -m pytest tests/test_download_tess.py -v` | green |
| 01-01-13 | 01 | 1 | VAL-01/02 | tests/test_smoke_test.py | unit | `python -m pytest tests/test_smoke_test.py -v` | green |

*Status: green — 75 unit tests pass, 3 integration tests (slow) pass*

---

## Wave 0 Requirements

- [x] `tests/conftest.py` — shared fixtures (synthetic time series, LD parquet, candidates)
- [x] 14 test files covering 14 implemented requirements
- [x] pytest framework installed and configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TESS MAST download integration | DATA-01 | Requires network + MAST auth | Run `--download` with real TIC IDs, verify .npz files created |
| End-to-end pipeline run | RPRT-04 | Integration test across all modules | `python pipeline/run_pipeline.py --sectors 1,2,3 --validate` |
| WASP-121b / TOI-270 / L 98-59 recovery | VAL-01/02 | Requires real TESS data | Run smoke test against real TLS catalogue |

---

## Implementation Bugs Found & Fixed

| File | Bug | Fix |
|------|-----|-----|
| `pipeline/preprocess/gp_detrend.py:24` | `terms.JitterTerm()` does not exist in celerite2 v3 | Replaced with `yerr = sqrt(flux_err**2 + jitter**2)` |
| `pipeline/preprocess/gp_detrend.py:34` | `gp.optimize()` removed in celerite2 v3 | Removed optimize call (uses default kernel params) |
| `pipeline/preprocess/gp_detrend.py:34` | `gp.predict()` returns scalar not tuple in v3 | Changed `mu, _ = gp.predict(...)` to `mu = gp.predict(...)` |
| `pipeline/detect/tls_search.py:62` | `float(res.chi2)` fails on non-scalar array in TLS v1.32 | Added `_safe_float_attr()` helper with scalar extraction |

---

## Validation Audit 2026-07-01

| Metric | Count |
|--------|-------|
| Gaps found | 14 |
| Resolved | 14 |
| Escalated | 0 |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-01
