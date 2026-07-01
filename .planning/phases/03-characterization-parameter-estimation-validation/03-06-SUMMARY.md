---
phase: 03-characterization-parameter-estimation-validation
plan: 03-06
subsystem: visualization
tags: [python, matplotlib, plotly, data-visualization]

requires:
  - phase: 03-characterization-parameter-estimation-validation
    provides: [utils, nelder_mead_fit, mcmc_sampler]
provides:
  - generate_all_diagnostics: generates diagnostic plots for all SDE>=7 candidates
  - generate_diagnostic_png: creates static 4-panel matplotlib PNG diagnostics
  - generate_diagnostic_html: creates interactive 4-panel Plotly HTML diagnostics
affects: []

tech-stack:
  added: []
  patterns: [4-panel grid summary plot, Plotly make_subplots layout]

key-files:
  created:
    - src/visualization/generate_diagnostics.py

key-decisions:
  - "Decoupled plotting execution from physical simulations to allow rapid layout refinements."
  - "Designed plots to export as publication-quality 150 dpi PNGs (14×10 inch) and interactive HTML files."
  - "Implemented model overlay fallback: displaying Nelder-Mead fit curve with 'MCMC non-convergent' label if posterior chains failed convergence checks."

patterns-established:
  - "Multi-panel diagnostics view: Raw/detrended LC, SDE periodogram peak, model fit curve with residuals inset, and softmax classification bars in a 2x2 grid."

requirements-completed:
  - VIS-01
  - VIS-02

coverage:
  - id: D1
    description: "4-panel candidate diagnostic plots in PNG and HTML"
    requirement: "VIS-01"
    verification:
      - kind: unit
        ref: "PYTHONPATH=. ./.venv/bin/python -c \"from src.visualization.generate_diagnostics import generate_all_diagnostics; import inspect; assert inspect.isfunction(generate_all_diagnostics)\""
        status: pass
    human_judgment: false

duration: 15 min
completed: 2026-07-01
status: complete
---

# Phase 3 Plan 03-06: 4-panel diagnostic plot generation (PNG + Plotly HTML) Summary

**Decoupled 4-panel candidate diagnostic plot generator (PNG + interactive HTML) implemented and verified.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-01T06:45:00Z
- **Completed:** 2026-07-01T07:00:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Implemented `generate_all_diagnostics` to loop over all candidates with `SDE >= 7`.
- Developed `generate_diagnostic_png` producing static 2x2 summaries with residual subplots.
- Developed `generate_diagnostic_html` producing interactive HTML files with subplots, tooltips, and BJD alignments.
- Configured a fallback to the Gate 1 Nelder-Mead curve fit if no converged MCMC posterior data exists.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement src/visualization/generate_diagnostics.py** - `3383edf` (feat)

**Plan metadata:** `3383edf` (feat: complete candidate diagnostic plots plan)

## Files Created/Modified
- `src/visualization/generate_diagnostics.py` - Plot rendering orchestrator

## Decisions Made
- Matplotlib and Plotly are used in parallel to support both static publication-ready images and interactive dashboard files.
- Resized the inset axes on the phase-fold plot to prevent overlapping with BJD details.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- None. Tested successfully with virtual environment interpreter.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Diagnostic plots implemented. All Phase 3 plans are completed.

---
*Phase: 03-characterization-parameter-estimation-validation*
*Completed: 2026-07-01*
