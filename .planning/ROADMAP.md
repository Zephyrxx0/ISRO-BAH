# Roadmap: ISRO BAH 2026 — Exoplanet Detection Pipeline

## Overview

Four vertically-integrated phases deliver an end-to-end ML pipeline that ingests TESS satellite photometry (~60,000 stars across 3 sectors), detects transit signals, classifies them into 4 astrophysical classes, estimates orbital parameters with calibrated uncertainties, and presents everything through an interactive Next.js dashboard and 4-page PDF report. Phases 1–3 are strictly sequential (hard pipeline dependencies). Phase 4 can partially overlap with Phase 3 (dashboard development with placeholder data during MCMC runs). CNN pre-training on Kepler DR24 must complete during the 7-day preparation window before hackathon Hour 0.

## Phases

- [x] **Phase 1: Foundation** — Data ingestion, preprocessing, and TLS period search on 60k light curves
- [ ] **Phase 2: Intelligence** — Feature extraction, CNN+XGBoost ensemble training, calibrated confidence scores
- [ ] **Phase 3: Characterization** — Two-gate MCMC parameter estimation, validation on known exoplanets, diagnostic visualizations
- [ ] **Phase 4: Presentation** — Interactive Next.js dashboard, candidate catalogue CSV, 4-page PDF report

## Phase Details

### Phase 1: Foundation — Data, Preprocessing & Detection
**Goal**: Pipeline ingests TESS data from MAST, preprocesses 60k light curves preserving transit signals, and detects transit candidates via TLS period search.
**Depends on**: Nothing (first phase; CNN Kepler pre-training prerequisite runs pre-hackathon)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, PREP-01, PREP-02, PREP-03, PREP-04, PREP-05, PREP-06, PREP-07, DET-01, DET-02, DET-03, DET-04, DET-05
**Success Criteria** (what must be TRUE):
  1. Pipeline downloads TESS 2-min cadence light curves for Sectors 1–3 (~60,000 stars) from MAST and stores them as .npz per TIC ID with a Parquet master catalogue
  2. All 60k light curves are preprocessed (quality-masked, 5σ-clipped, normalized, biweight-detrended at window_length≥0.75d) without erasing WASP-121b's transit — verified by post-detrending detection
  3. TLS period search runs on all preprocessed targets (0.5–30 day range, 50k frequency steps) producing a candidate table with SDE, SNR, CDPP, and period per star in Parquet
  4. Multi-planet iterative search (3 iterations per star) recovers all 3 planets of TOI-270 (Sector 3) and all 3 planets of L 98-59 (Sector 2)
  5. Pipeline applies 3-tier SDE gating — SDE<5 discarded, 5≤SDE<7 kept as sub-threshold, SDE≥7 proceed to full pipeline — and validates top candidates with BLS
**Plans**: TBD

### Phase 2: Intelligence — Feature Engineering & ML Classification
**Goal**: Pipeline extracts 8+ engineered features per candidate, trains CNN+XGBoost ensemble on Kepler pre-trained weights, classifies all SDE≥5 candidates into 4 classes, and produces temperature-scaled confidence scores with ECE<0.04.
**Depends on**: Phase 1 (requires TLS periods, candidate table, and preprocessed light curves)
**Requirements**: FEAT-01, FEAT-02, FEAT-03, FEAT-04, CLAS-01, CLAS-02, CLAS-03, CLAS-04, CLAS-05, CLAS-06, CLAS-07, CONF-01, CONF-02, CONF-03, MLOP-01, MLOP-02
**Success Criteria** (what must be TRUE):
  1. Every SDE≥5 candidate has 8+ engineered features computed (odd/even depth, centroid shift, V-shape, CROWDSAP, secondary eclipse depth, duration/period ratio, SDE, SNR) with TPF-based centroid analysis on top 200
  2. Dual-View CNN (Kepler DR24 pre-trained → TESS ExoFOP fine-tuned with 7× augmentation) and XGBoost (stratified k-fold, F1-macro) independently classify all candidates; ensemble (0.6×CNN + 0.4×XGBoost) outputs 4-class softmax probabilities
  3. Classification accuracy exceeds 90% on held-out ExoFOP test set with planet recall >85%, planet precision >80%, and false positive rate <10% — validated by confusion matrix and SHAP TreeExplainer feature importance summary
  4. Temperature-scaled confidence scores are calibrated (ECE < 0.04) with Gold (>0.90), Silver (0.70–0.90), and Bronze (<0.70) tiers assigned to every classified candidate
  5. MLflow tracks both training experiments (Kepler CNN pre-training, TESS fine-tuning + XGBoost ensemble) logging hyperparameters, loss curves, validation metrics, confusion matrices, ECE before/after calibration, and model artifacts
**Plans**: TBD

### Phase 3: Characterization — Parameter Estimation & Validation
**Goal**: Pipeline estimates orbital parameters via two-gate MCMC (Nelder-Mead gate → emcee gate), validates detection and parameter recovery against known exoplanets, and generates 4-panel diagnostic plots plus completeness map for every significant candidate.
**Depends on**: Phase 2 (requires classification outputs, confidence scores, and calibrated tiers to gate parameter estimation)
**Requirements**: PARM-01, PARM-02, PARM-03, PARM-04, PARM-05, PARM-06, VAL-01, VAL-02, VAL-03, VAL-04, VAL-05, VIS-01, VIS-02, VIS-03
**Success Criteria** (what must be TRUE):
  1. Two-gate parameter estimation runs: Nelder-Mead batman fits on SDE≥7+confidence>0.70 candidates (~50), then full emcee MCMC (32 walkers, 5000 steps) on top 15 Gold-tier candidates (confidence>0.85) with acceptance fraction 0.2–0.5
  2. MCMC posteriors report median ± 1σ (16th/84th percentile) for orbital period P, transit duration T₁₄, transit depth δ, Rp/Rs, and inclination — with corner plots for converged chains; parameter recovery validates period within 0.1% and depth within 5% against published values
  3. TRICERATOPS+ computes FPP<1.5% and NFPP<0.1% on top 5 Gold planet candidates qualifying as "Validated Planets"; SHERLOCK benchmark confirms pipeline recovery against published 98% TOI recovery rate
  4. Pre-pipeline validation pass (Day 1) confirms recovery of WASP-121b; end-to-end validation confirms recovery of TOI-270 (3 planets), L 98-59 (3 planets), and TOI-700 d with correct periods and depths
  5. Every SDE≥7 candidate receives a 4-panel diagnostic plot (raw+detrended LC with transit epochs, TLS periodogram with peak annotated, phase-folded LC + batman model overlaid with residuals, classifier softmax bar chart) exported as publication-quality PNG (150 dpi) and interactive Plotly HTML; completeness map shows recovery fraction vs. depth/period from synthetic injection
**Plans**: TBD

### Phase 4: Presentation — Dashboard & Report
**Goal**: Interactive Next.js read-only dashboard displays all pipeline outputs with filterable candidate table and celestial star map; candidate catalogue CSV and 4-page PDF report are generated and ready for ISRO judge presentation.
**Depends on**: Phase 3 (requires pre-rendered diagnostic plots, parameter estimates, and classification outputs for dashboard and report)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, RPRT-01, RPRT-02, RPRT-03, RPRT-04
**Success Criteria** (what must be TRUE):
  1. Next.js dashboard displays a filterable/sortable candidate table (TIC ID, period, depth, SDE, classification, disposition, confidence tier) — all data read from pre-rendered outputs in `/outputs/`
  2. Clicking any TIC ID in the dashboard opens a per-star 4-panel diagnostic view with pre-rendered images; celestial star map (Leaflet.js) shows Gold-tier planet candidate positions by RA/Dec
  3. Candidate catalogue CSV is output with all required columns: TIC ID, period, depth, duration, SDE, SNR, classification label, disposition (PLANET CANDIDATE / ECLIPSING BINARY / BACKGROUND BLEND / STELLAR VARIABILITY / SUB-THRESHOLD), confidence score, confidence tier, and parameter uncertainties
  4. 4-page PDF report is generated: Page 1 — Methodology (flowchart + confusion matrix), Page 2 — Results (candidate table + best planet highlight), Page 3 — Validation (TRICERATOPS+ FPP + SHERLOCK comparison + recovery tests + completeness map), Page 4 — Uncertainties (MCMC posteriors + assumptions + limitations)
  5. Entire pipeline executes from raw data ingestion to final report via single command `python run_pipeline.py --sectors 1,2,3` producing all outputs in `/outputs/` directory
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases 1–3 are strictly sequential (hard data dependencies). Phase 4 can begin in parallel with Phase 3 using placeholder data; final integration requires Phase 3 outputs. CNN Kepler pre-training must complete during the 7-day preparation window before Phase 2.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/1 | Complete | 2026-07-01 |
| 2. Intelligence | 0/5 | Planned | - |
| 3. Characterization | 0/0 | Not started | - |
| 4. Presentation | 0/0 | Not started | - |
