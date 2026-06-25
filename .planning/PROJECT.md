# Exoplanet Detection Pipeline (ISRO BAH 2026 — PS-07)

## What This Is

An end-to-end AI/ML pipeline that ingests TESS satellite photometry (light curves), detects periodic transit signals, classifies them into 4 astrophysical classes (planet candidate, eclipsing binary, background blend, stellar variability), and estimates orbital parameters with calibrated confidence scores. Built for the ISRO Bharatiya Antariksh Hackathon 2026 Grand Finale (6–7 August 2026), targeting 3 TESS sectors (~60,000 stars).

## Core Value

Reliably distinguish true exoplanet transits from astrophysical false positives (eclipsing binaries, background blends, starspots) in noisy TESS light curves, with calibrated uncertainty on both classification and orbital parameters — enabling mission planners to triage candidates without manual vetting.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Ingest and preprocess 3 TESS sectors (~60k 2-min cadence light curves) from MAST/TIC
- [ ] Run TLS period search with iterative multi-planet signal removal on all targets
- [ ] Extract 8+ engineered features per candidate (odd/even depth, centroid shift, CROWDSAP, V-shape, secondary eclipse, duration/period ratio, SDE, SNR)
- [ ] Train Dual-View CNN (AstroNet-style) on Kepler DR24 pre-training + TESS ExoFOP fine-tuning with 7× augmentation (including synthetic transit injection)
- [ ] Classify every SDE≥5 candidate into 4 classes via CNN+XGBoost ensemble (0.6×CNN + 0.4×XGB)
- [ ] Produce temperature-scaled confidence scores (Gold >0.90, Silver 0.70–0.90, Bronze <0.70) with ECE < 0.04
- [ ] Run batman+MCMC parameter estimation on top 15 Gold-tier planet candidates (SDE≥7, PC confidence>0.85)
- [ ] Compute TRICERATOPS+ FPP/NFPP on top 5 Gold planet candidates
- [ ] Generate 4-panel diagnostic plots (raw LC, TLS periodogram, phase-fold+model, classifier softmax) per SDE≥7 candidate
- [ ] Build Next.js interactive dashboard (candidate table, per-star diagnostics, celestial star map)
- [ ] Output candidate catalogue CSV with TIC ID, period, depth, duration, SDE, classification, disposition, confidence tier
- [ ] Validate recovery on WASP-121b (Sector 1), TOI-270 (Sector 3), L 98-59 (Sector 2), TOI-700 d
- [ ] Produce 4-page PDF report (Methodology, Results, Validation, Uncertainties)
- [ ] Log all training runs to MLflow for reproducibility

### Out of Scope

- Multi-sector search beyond 3 sectors — — pipeline designed for 3-sector delivery; scalable claim in pitch only
- Real-time streaming data processing — — offline batch pipeline, no streaming requirement
- Full atmospheric characterisation — — transit spectroscopy not in scope
- Ground-truth follow-up observations — — validation against published catalogs only
- GPU model training from scratch during the hackathon — — pre-train ahead of finale
- OAuth or user authentication for dashboard — — read-only static viewer

## Context

**Hackathon:** ISRO Bharatiya Antariksh Hackathon 2026, Problem Statement PS-07. 30-hour grand finale. Team of 3–4. Must deliver: detection + classification + parameter estimation + confidence intervals.

**Domain:** Exoplanet transit detection from TESS 2-min cadence photometry. The transit signal is an ~84 ppm dip for Earth-sized planets — buried in instrumental systematics, correlated (red) noise, and astrophysical false positives. The core ML problem is 4-class classification on phase-folded time-series data.

**Key prior decisions (from ADRs):**
- ADR-0001: Dual-View CNN (AstroNet) over Bi-LSTM+Transformer
- ADR-0002: 3 sectors (1, 2, 3) over single sector
- ADR-0003: 7× augmentation with synthetic transit injection
- ADR-0004: Kepler pre-training + TESS fine-tuning over TESS-only

**Domain glossary:** See `CONTEXT.md` for canonical terminology (35 terms across 6 clusters).

## Constraints

- **Timeline**: 7 days of preparation + 30-hour hackathon finale (6–7 Aug 2026)
- **Compute**: Single NVIDIA T4 GPU (Colab free tier or equivalent). No HPC.
- **Data**: Must use TESS 2-min cadence data from MAST TIC archive (required by problem statement)
- **Team**: 3–4 members, all students
- **Tech Stack**: Python 3.10+ (pipeline), Next.js (dashboard), TensorFlow/Keras (CNN), XGBoost, SHAP, MLflow
- **Storage**: .npz per light curve + Parquet master catalogue
- **Report**: 4-page PDF maximum

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Dual-View CNN over Bi-LSTM+Transformer | Peer-reviewed (Shallue & Vanderburg 2018), judges recognize it, TensorFlow API simpler for CNNs | — Pending |
| 3 sectors (1, 2, 3) over single sector | Extends detectable period range, cross-sector validation, fits 7-day prep window | — Pending |
| 7× augmentation with synthetic transit injection | Addresses shallow-transit gap in real labels, produces completeness map, trains in <3.5h on T4 | — Pending |
| Kepler pre-train + TESS fine-tune over TESS-only | Follows ExoMiner++ pattern, 34k extra samples, stronger shape prior, handles domain shift via fine-tuning | — Pending |
| TLS primary + BLS validation | TLS detects 10–15% more small planets, GPU-accelerated; BLS validates top candidates | — Pending |
| Instrumentals as preprocessing gate, not classifier class | Keeps classifier focused on astrophysical signals; TESS quality flags handle hardware artefacts | — Pending |
| 4-class taxonomy (PC, EB, Blend, Other FP) | Matches problem statement requirements; instrumentals handled pre-classification | — Pending |
| Centroid analysis as core feature | Blends are the hardest FP class; TPF pixels needed for centroid shift; adds ~2h | — Pending |
| .npz + Parquet storage over HDF5 | Zero-dependency beyond NumPy, columnar querying, per-star corruption isolation | — Pending |
| 2-tier detrending (biweight bulk + GP on top 100) | biweight is fast for 60k LCs; celerite2 Matérn-3/2 models correlated noise for top candidates | — Pending |
| Per-star limb darkening from TICv8 | Avoids systematic depth error from hard-coded coefficients; free in compute on 15 MCMC runs | — Pending |
| Two-gate MCMC (Nelder-Mead SDE>7+p>0.70 → MCMC SDE>7+p>0.85 top 15) | Separates cheap fit from expensive sampling; aligns with Section 11 uncertainty strategy | — Pending |
| Next.js read-only dashboard over pre-generated static files | Python pipeline pre-renders all visuals; Next.js reads from /outputs/; no live Python backend needed | — Pending |
| Mask 13-day data gaps (don't interpolate) | Interpolation over 13 days creates synthetic structure; TLS handles masked arrays natively | — Pending |
| Stratified sampling + F1-macro over class weights | Classes aren't severely imbalanced (2:1 worst); F1-macro penalizes ignoring any class | — Pending |
| SHERLOCK as verification-only on top 5 | Independent second-opinion; 98% TOI recovery benchmark; avoids redundant full pipeline | — Pending |
| TRICERATOPS+ on top 5 Gold candidates | Community-standard FPP/NFPP validation; "Validated Planet" language from professional papers | — Pending |
| 4-page report with dedicated validation page | Maps to 4 evaluation criteria: Methods, Detection+Classification, Validation Rigor, Parameter Uncertainty | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 25 Jun 2026 after initialization*
