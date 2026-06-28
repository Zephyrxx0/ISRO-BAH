# Phase 03: Characterization — Parameter Estimation & Validation - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning

## Phase Boundary

Phase 3 takes Phase 2's classified candidates (with confidence tiers and SDE values), runs two-gate MCMC parameter estimation (Nelder-Mead batman fit on SDE≥7+confidence>0.70 candidates, then full emcee MCMC on top 15 Gold-tier candidates with confidence>0.85), validates parameter recovery against known exoplanets (WASP-121b, TOI-270, L 98-59, TOI-700 d), runs TRICERATOPS+ and SHERLOCK for independent verification of top 5 Gold candidates, and generates 4-panel diagnostic plots plus completeness map for every SDE≥7 candidate. All results stored alongside the master Parquet catalogue for Phase 4 consumption.

## Implementation Decisions

### MCMC Priors & Parameter Setup
- **D-01:** Uniform priors with wide bounds for all MCMC parameters. Bounds set dynamically per target: period from [TLS_period ± 3×TLS_uncertainty], depth from TLS depth ± 5σ, Rp/Rs from TICv8 stellar radius ± 3σ.
- **D-02:** Eccentricity fixed at e=0, ω=90° (circular orbits assumed). Reduces parameter space by 2, avoids degeneracy with duration and impact parameter.
- **D-03:** Limb darkening coefficients fixed at TICv8 Claret & Bloemen (2011) quadratic values during MCMC sampling — not sampled as free parameters. Avoids degeneracy with impact parameter and depth.

### TRICERATOPS+ & SHERLOCK Integration
- **D-04:** Both tools executed as subprocesses with isolated conda environments (`subprocess.run()`). Each tool gets its own env to avoid dependency conflicts with the main pipeline (astropy, lightkurve stack).
- **D-05:** Conda environments pre-built during the 7-day preparation window. Pipeline activates existing envs at runtime — no dependency resolution during the 30-hour hackathon.
- **D-06:** Fallback on tool failure: skip the failing tool, flag in catalogue (`FPP not computed` / `SHERLOCK comparison unavailable`), continue pipeline. TRICERATOPS+ and SHERLOCK are verification-only, not gating.
- **D-07:** Results stored as `data/verification/{tool_name}/{TIC_ID}.json` with key values (FPP, NFPP, SHERLOCK_verdict) appended as new columns to master Parquet.

### Validation Campaign Structure
- **D-08:** Dedicated `validate.py` script for known validation planets — loads published parameters from literature, runs batman+MCMC directly on preprocessed light curves, compares output vs. published values. Skips full detection pipeline (TLS, features, classification) for these targets.
- **D-09:** TOI-700 d handled as special validation-only target — download Sector 4 data separately outside the 60k batch. Requires ~10 min extra download to satisfy VAL-03 (small-planet detection validation).
- **D-10:** Validation success = quantitative parameter recovery meeting PARM-06 tolerances: period within 0.1% of published, depth within 5%, duration within 10%. Each parameter checked independently.
- **D-11:** Validation results stored as structured JSON per target (`data/validation/{planet_name}.json`) with published vs. recovered parameters, pass/fail per parameter, summary verdict. Also written to JSON-lines pipeline log.

### Diagnostic Plot Pipeline
- **D-12:** Separate `generate_diagnostics.py` visualization script — reads from Parquet + .npz files, generates all PNG (150 dpi) + Plotly HTML files to `outputs/plots/`. Decoupled from MCMC computation — can be re-run independently.
- **D-13:** MCMC non-convergence fallback: show Nelder-Mead batman fit overlay instead of MCMC model. Flag plot with "MCMC non-convergent — showing Nelder-Mead fit" annotation. Corner plot replaced by simple parameter table from NM fit.
- **D-14:** Plotly HTML exports use standard interactivity: zoom, pan, hover tooltips with values, save-as-PNG. Hover annotations on transit epochs in raw LC panel. Clickable periodogram peaks showing period+SDE.
- **D-15:** Completeness map: 2D recovery fraction heatmap. Depth axis (50–2000 ppm, log scale) × period axis (0.5–30 days, log scale), 20×20 grid. Recovery fraction = (injected transits detected with SDE≥7) / total injected per cell. Single PNG + Plotly HTML output.

### Agent's Discretion
- (none — user made explicit choices on all questions)

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture Decisions (ADRs)
- `docs/adr/0001-dual-view-cnn-architecture.md` — CNN architecture; Phase 3 diagnostic plots reuse PhaseFolder 2001+201 views
- `docs/adr/0002-three-sector-search.md` — 3-sector scope; Phase 3 validation spans Sectors 1-3 + TOI-700 d from Sector 4
- `docs/adr/0003-synthetic-transit-injection-augmentation.md` — 7× augmentation; Phase 3 completeness map aggregates synthetic injection recovery results
- `docs/adr/0004-kepler-pretrain-tess-finetune.md` — Pre-training strategy; Phase 3 is downstream of fine-tuned model outputs

### Project Planning
- `.planning/PROJECT.md` — Key Decisions table (18 decisions), constraints, two-gate MCMC decision, TRICERATOPS+ and SHERLOCK decisions
- `.planning/REQUIREMENTS.md` — Phase 3 owns: PARM-01 through PARM-06, VAL-01 through VAL-05, VIS-01 through VIS-03
- `.planning/ROADMAP.md` — Phase 3 goal, 5 success criteria, dependency on Phase 2
- `.planning/phases/01-foundation-data-preprocessing-detection/01-CONTEXT.md` — Phase 1 patterns: modular step functions, file-based checkpoints, tqdm, JSON-lines logging, mirror directory layout
- `.planning/phases/02-intelligence-feature-engineering-ml-classification/02-CONTEXT.md` — Phase 2 outputs consumed by Phase 3: classification labels, confidence scores, feature columns in master Parquet, PhaseFolder 2001+201 views, CuPy preference

### Data Contract
- `data/catalogue/schema.md` — Parquet column specification (created by Phase 1, extended by Phase 2, Phase 3 reads classification/confidence columns and appends parameter/validation columns)

### Domain Glossary
- `CONTEXT.md` — 35 canonical terms across 6 clusters

## Existing Code Insights

### Reusable Assets
- No existing codebase — Phase 1 and Phase 2 are under development. Phase 3 is the third implementation phase.
- PhaseFolder 2001+201 views (Phase 2) reused directly in diagnostic plot panel 3 (phase-folded + model overlay).
- Master Parquet catalogue (created Phase 1, extended Phase 2) is the single source of truth for Phase 3 inputs and outputs.

### Established Patterns
- Modular step functions with file-based checkpoints (Phase 1 pattern) — apply to MCMC and plot generation steps.
- Structured directory layout: `data/preprocessed/sector{N}/`, `data/catalogue/`, `outputs/`
- .npz per TIC ID + Parquet master catalogue
- tqdm progress bars + JSON-lines logging
- `run_pipeline.py` CLI entry point — Phase 3 modules integrate here
- Standalone scripts for one-time operations (Phase 2 pattern: `train_kepler.py`, `train_cnn_finetune.py`)
- CuPy preferred over NumPy when GPU available (Phase 2 decision)

### Integration Points
- Phase 3 reads from Phase 2 outputs: `data/catalogue/master.parquet` (classification, confidence, features), `data/preprocessed/sector{N}/TIC_*_preprocessed.npz`, `data/folded/TIC_*_folded.npz`
- Phase 3 writes to: `data/catalogue/master.parquet` (appends MCMC parameters, verification results), `data/mcmc/{TIC_ID}/` (chain files, corner plots), `data/validation/` (validation JSONs), `data/verification/{triceratops,sherlock}/{TIC_ID}.json`, `outputs/plots/` (diagnostic PNGs + Plotly HTML), `outputs/completeness/` (completeness map)
- Phase 4 consumes Phase 3 outputs: all diagnostic plots, parameter estimates, verification results for dashboard and PDF report

## Specific Ideas

- MCMC chains and corner plots stored per-TIC-ID for debugging and audit trail — follow Phase 1 "keep all intermediates" pattern
- Validation script (`validate.py`) is separate from main `run_pipeline.py` — validation is a manual, once-per-event activity on known targets
- Diagnostic plot script (`generate_diagnostics.py`) is decoupled and re-runnable — allows layout refinements without recomputing MCMC
- TRICERATOPS+ and SHERLOCK conda envs are pre-built assets tracked alongside Kepler pre-trained model (both are prep-week prerequisites)

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 03-characterization-parameter-estimation-validation*
*Context gathered: 2026-06-28*
