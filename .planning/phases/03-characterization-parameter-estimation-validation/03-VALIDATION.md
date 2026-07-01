---
phase: 03
slug: characterization-parameter-estimation-validation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-01
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (no pyproject.toml — conftest.py-driven) |
| **Config file** | `tests/conftest.py` |
| **Quick run command** | `PYTHONPATH=. ./.venv/bin/pytest tests/test_utils.py tests/test_validate.py -v` |
| **Full suite command** | `PYTHONPATH=. ./.venv/bin/pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds (Phase 3 tests only) |

---

## Sampling Rate

- **After every task commit:** Run `PYTHONPATH=. ./.venv/bin/pytest tests/test_*.py -q`
- **After every plan wave:** Run `PYTHONPATH=. ./.venv/bin/pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | PARM-06 | — | __init__.py exports correct symbols | import | `PYTHONPATH=. ./.venv/bin/python -c "from src.characterization import compute_a_rs, filter_gate1_candidates"` | ✅ | ✅ green |
| 03-01-02 | 01 | 1 | PARM-06 | — | compute_a_rs, get_limb_darkening, filter_gate1_candidates, filter_gate2_candidates, append_to_parquet, ensure_directories, load_phase_folded, log_jsonl | unit | `pytest tests/test_utils.py -v` | ✅ | ✅ green |
| 03-01-03 | 01 | 1 | PARM-06 | — | validation/__init__.py exports VALIDATION_TARGETS | import | `PYTHONPATH=. ./.venv/bin/python -c "from src.validation import VALIDATION_TARGETS"` | ✅ | ✅ green |
| 03-01-04 | 01 | 1 | PARM-06 | — | 8 validation targets with published params | unit | `PYTHONPATH=. ./.venv/bin/python -c "from src.validation.published_params import VALIDATION_TARGETS; assert len(VALIDATION_TARGETS) == 8"` | ✅ | ✅ green |
| 03-01-05 | 01 | 1 | PARM-06 | — | visualization/__init__.py exports symbols | import | `PYTHONPATH=. ./.venv/bin/python -c "from src.visualization import generate_all_diagnostics"` | ✅ | ✅ green |
| 03-02-01 | 02 | 1 | PARM-01 | — | Nelder-Mead batman fit run_gate1() | unit | `pytest tests/test_nelder_mead.py -v` | ✅ | ✅ green |
| 03-02-02 | 02 | 1 | PARM-01 | — | fit_single_candidate recovers Rp/Rs within 10% | unit | `pytest tests/test_nelder_mead.py -v` | ✅ | ✅ green |
| 03-03-01 | 03 | 2 | PARM-02,03,04,05 | — | emcee MCMC run_gate2() with HDF5 backend | import | `PYTHONPATH=. ./.venv/bin/python -c "from src.characterization.mcmc_sampler import run_gate2"` | ✅ | ✅ green |
| 03-03-02 | 03 | 2 | PARM-02,03,04 | — | _compute_bounds, _extract_posteriors | unit | `pytest tests/test_mcmc_sampler.py -v` | ✅ | ✅ green |
| 03-04-01 | 04 | 2 | VAL-01,02,03,PARM-06 | — | run_validation(), validate_parameter_recovery() | import | `PYTHONPATH=. ./.venv/bin/python -c "from src.validation.validate import run_validation"` | ✅ | ✅ green |
| 03-04-02 | 04 | 2 | PARM-06 | — | Tolerance logic: period 0.1%, depth 5%, duration 10% | unit | `pytest tests/test_validate.py -v` | ✅ | ✅ green |
| 03-05-01 | 05 | 3 | VAL-04 | — | TRICERATOPS+ runner with _classify_fpp | unit | `pytest tests/test_triceratops_runner.py -v` | ✅ | ✅ green |
| 03-05-02 | 05 | 3 | VAL-05 | — | SHERLOCK runner with _parse_sherlock_output | unit | `pytest tests/test_sherlock_runner.py -v` | ✅ | ✅ green |
| 03-06-01 | 06 | 3 | VIS-01,02 | — | 4-panel diagnostic PNG/HTML generation | unit | `pytest tests/test_generate_diagnostics.py -v` | ✅ | ✅ green |
| 03-07-01 | 07 | 3 | VIS-03 | — | Completeness map injection-recovery | import | `PYTHONPATH=. ./.venv/bin/python -c "from src.characterization.completeness import generate_completeness_map"` | ✅ | ✅ green |
| 03-07-02 | 07 | 3 | VIS-03 | — | _inject_transit and completeness visualization | unit | `pytest tests/test_completeness.py -v` | ✅ | ✅ green |

*Status: ✅ green*

---

## Wave 0 Requirements

- [x] `tests/test_utils.py` — 22 tests for shared utilities (PARM-06)
- [x] `tests/test_triceratops_runner.py` — 14 tests for FPP classification (VAL-04)
- [x] `tests/test_sherlock_runner.py` — 10 tests for output parsing (VAL-05)
- [x] `tests/test_generate_diagnostics.py` — 10 tests for diagnostic helpers (VIS-01, VIS-02)
- [x] `tests/test_completeness.py` — 5 tests for injection-recovery (VIS-03)
- [x] `tests/conftest.py` — shared fixtures (Phase 1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TRICERATOPS+ subprocess execution (conda env) | VAL-04 | Requires pre-built `triceratops_env` conda environment + MAST access | `PYTHONPATH=. ./.venv/bin/python -m src.characterization.triceratops_runner` |
| SHERLOCK subprocess execution (conda env) | VAL-05 | Requires pre-built `sherlock_env` conda environment + SHERLOCK installation | `PYTHONPATH=. ./.venv/bin/python -m src.characterization.sherlock_runner` |
| Full validation campaign (8 targets) | VAL-01,02,03 | Requires preprocessed light curves for all 8 validation targets | `PYTHONPATH=. ./.venv/bin/python -m src.validation.validate --all` |
| Full diagnostic plot generation | VIS-01,02 | Requires preprocessed + folded + MCMC data on disk | `PYTHONPATH=. ./.venv/bin/python -m src.visualization.generate_diagnostics` |
| Completeness map computation (1000 TLS runs) | VIS-03 | ~30 min runtime, requires many preprocessed LCs | `PYTHONPATH=. ./.venv/bin/python -m src.characterization.completeness` |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-01

---

## Validation Audit 2026-07-01

| Metric | Count |
|--------|-------|
| Gaps found | 6 |
| Resolved | 6 |
| Escalated | 0 |

### Resolution Summary

| # | Gap | Plan | File Created | Tests | Status |
|---|-----|------|-------------|-------|--------|
| 1 | Shared utilities untested | 03-01 | `tests/test_utils.py` | 22 | green |
| 2 | TRICERATOPS+ _classify_fpp untested | 03-05 | `tests/test_triceratops_runner.py` | 14 | green |
| 3 | SHERLOCK _parse_sherlock_output untested | 03-05 | `tests/test_sherlock_runner.py` | 10 | green |
| 4 | Diagnostic plot helpers untested | 03-06 | `tests/test_generate_diagnostics.py` | 10 | green |
| 5 | Completeness injection untested | 03-07 | `tests/test_completeness.py` | 5 | green |
| 6 | _load_candidate_data untested | 03-06 | `tests/test_generate_diagnostics.py` | 4 | green |

**Total:** 61 new tests across 5 test files. All passing. 0 escalated.
