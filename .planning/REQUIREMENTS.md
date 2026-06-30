# Requirements: ISRO BAH 2026 — Exoplanet Detection Pipeline

**Defined:** 25 Jun 2026
**Core Value:** Reliably distinguish true exoplanet transits from astrophysical false positives in noisy TESS light curves, with calibrated uncertainty on both classification and orbital parameters.

## v1 Requirements

Requirements for the 30-hour hackathon grand finale. Each maps to pipeline stages and roadmap phases.

### Data Ingestion

- [x] **DATA-01**: Pipeline downloads TESS 2-min cadence light curves for Sectors 1, 2, and 3 (~60,000 stars) from MAST via lightkurve/astroquery
- [ ] **DATA-02**: Pipeline downloads Target Pixel Files (TPFs) via TESScut for centroid analysis on top SDE ≥ 7 candidates (deferred to Phase 2)
- [ ] **DATA-03**: Pipeline downloads ExoFOP-TESS TOI disposition table for training labels (Phase 2)
- [ ] **DATA-04**: Pipeline downloads Kepler DR24 TCE catalog (AstroNet dataset, 34,032 labeled samples) for CNN pre-training (Phase 2 prep)
- [x] **DATA-05**: Pipeline stores raw data as .npz per TIC ID with a Parquet master catalogue

### Preprocessing

- [x] **PREP-01**: Pipeline removes NaNs and quality-flagged cadences (AttitudeTweak, SafeMode, CosmicRay, ManualExclude)
- [x] **PREP-02**: Pipeline performs sigma-clipping at 5σ to remove outliers, then normalizes flux to median = 1.0
- [x] **PREP-03**: Pipeline detrends all 60k light curves using biweight method (Wotan, window_length=0.75d) preserving transit shapes
- [x] **PREP-04**: Pipeline applies Gaussian Process detrending (celerite2 Matérn-3/2) on top 100 SDE ≥ 7 candidates to model correlated noise
- [x] **PREP-05**: Pipeline masks (does not interpolate) 13-day TESS data gaps, flagging gap-edge cadences as unreliable
- [x] **PREP-06**: Pipeline excludes stars with TESS magnitude < 6 (saturation artefacts) and light curves with < 500 valid cadences
- [x] **PREP-07**: Pipeline extracts per-star limb darkening coefficients from TICv8 using Claret & Bloemen (2011) tables for batman inputs

### Detection — Period Search

- [x] **DET-01**: Pipeline runs TLS (Transit Least Squares) as primary period search on all preprocessed light curves (period range 0.5–30 days, 50k frequency steps)
- [x] **DET-02**: Pipeline runs BLS (Box Least Squares) as validation check on top candidates
- [x] **DET-03**: Pipeline performs iterative multi-planet search (3 iterations) — masking found signals and re-running TLS
- [x] **DET-04**: Pipeline computes SDE, SNR, and CDPP for every detected signal
- [x] **DET-05**: Pipeline applies 3-tier SDE gating: SDE < 5 → discard, 5 ≤ SDE < 7 → keep as sub-threshold, SDE ≥ 7 → full pipeline

### Feature Extraction

- [ ] **FEAT-01**: Pipeline extracts 8+ engineered features per candidate: odd/even depth difference, secondary eclipse depth, centroid shift, V-shape metric, CROWDSAP, duration/period ratio, SDE, SNR
- [ ] **FEAT-02**: Pipeline performs centroid shift analysis from TPF data — flux-weighted centroid in-transit vs. out-of-transit; shift > 3σ → blend indicator
- [ ] **FEAT-03**: Pipeline applies CROWDSAP pre-filter: contamination < 0.5 blocks Planet Candidate classification; contamination < 0.9 triggers centroid investigation
- [ ] **FEAT-04**: Pipeline phase-folds each candidate at its TLS period into 2001-point global view + 201-point local zoom view for CNN input

### Classification

- [ ] **CLAS-01**: CNN is pre-trained on Kepler DR24 labeled dataset (34,032 TCEs) during preparation week
- [ ] **CLAS-02**: CNN is fine-tuned on ExoFOP-TESS TOI labels with 7× augmentation (noise injection + transit jitter + synthetic transit injection at 50–200 ppm depths)
- [ ] **CLAS-03**: XGBoost classifier is trained on 8+ engineered features for 4-class discrimination
- [ ] **CLAS-04**: Ensemble (0.6 × CNN + 0.4 × XGBoost) produces 4-class softmax probabilities per SDE ≥ 5 candidate
- [ ] **CLAS-05**: Pipeline produces per-class evaluation metrics: precision, recall, F1, confusion matrix heatmap, ROC-AUC (one-vs-rest)
- [ ] **CLAS-06**: Overall classification accuracy > 90% on ExoFOP-labeled held-out test set; planet recall > 85%; planet precision > 80%; FPR < 10%
- [ ] **CLAS-07**: SHAP TreeExplainer generates feature importance summary plot explaining XGBoost classification decisions

### Confidence & Calibration

- [ ] **CONF-01**: Pipeline applies temperature scaling to ensemble softmax outputs, calibrated on held-out validation set
- [ ] **CONF-02**: Pipeline assigns Gold (> 0.90), Silver (0.70–0.90), Bronze (< 0.70) confidence tiers to all classified candidates
- [ ] **CONF-03**: Pipeline reports Expected Calibration Error (ECE < 0.04 target) with per-class reliability diagrams

### Parameter Estimation

- [x] **PARM-01**: Pipeline runs batman Mandel-Agol transit model (scipy Nelder-Mead fit) on candidates with SDE ≥ 7 AND PC confidence > 0.70
- [x] **PARM-02**: Pipeline runs full emcee MCMC (32 walkers, 5000 steps) on top 15 Gold candidates ranked by SDE × PC confidence, gated on PC confidence > 0.85
- [x] **PARM-03**: MCMC output reports median ± 1σ (16th/84th percentile) for orbital period P, transit duration T₁₄, transit depth δ, Rp/Rs, inclination
- [x] **PARM-04**: MCMC chains validated with acceptance fraction 0.2–0.5; non-converging chains fall back to Nelder-Mead fit
- [x] **PARM-05**: Pipeline generates corner plot (corner package) showing 2D posterior distributions with 1σ, 2σ contours per MCMC candidate
- [x] **PARM-06**: Parameter recovery validated against published values: period within 0.1% for SNR > 10, depth within 5%, duration within 10%

### Validation

- [x] **VAL-01**: Pre-pipeline validation pass on Day 1 confirms recovery of WASP-121b (P=1.27d, Sector 1)
- [x] **VAL-02**: Pipeline validates multi-planet recovery on TOI-270 (3 planets, Sector 3) and L 98-59 (3 planets, Sector 2)
- [x] **VAL-03**: Pipeline validates small-planet detection on TOI-700 d (Sector 4 or equivalent shallow transit target in Sectors 1-3)
- [x] **VAL-04**: TRICERATOPS+ computes FPP and NFPP on top 5 Gold planet candidates; reports FPP < 1.5% and NFPP < 0.1% as Validated Planet thresholds
- [x] **VAL-05**: SHERLOCK benchmark comparison on top 5 candidates (independent verification, cited against 98% TOI recovery rate)

### Visualization

- [x] **VIS-01**: Pipeline generates 4-panel diagnostic plot per SDE ≥ 7 candidate: (1) raw + detrended light curve with transit epochs, (2) TLS periodogram with peak annotated, (3) phase-folded light curve + batman model overlaid with residuals, (4) classifier softmax bar chart
- [x] **VIS-02**: Diagnostic plots exported as PNG (publication-quality, 150 dpi) and interactive HTML (Plotly)
- [x] **VIS-03**: Pipeline generates completeness map: recovery fraction as function of transit depth (50–2000 ppm) and orbital period, from synthetic injection results

### Dashboard

- [ ] **DASH-01**: Next.js read-only dashboard displays pre-rendered outputs from `/outputs/` directory
- [ ] **DASH-02**: Dashboard includes filterable/sortable candidate table (TIC ID, period, depth, SDE, classification, disposition, confidence tier)
- [ ] **DASH-03**: Clicking a TIC ID shows per-star 4-panel diagnostic view with pre-rendered images
- [ ] **DASH-04**: Dashboard includes celestial star map (RA/Dec scatter plot via Leaflet.js) showing Gold-tier planet candidate positions

### Report & Deliverables

- [ ] **RPRT-01**: Pipeline produces 4-page PDF report: Page 1 Methodology (flowchart + confusion matrix), Page 2 Results (candidate table + best planet), Page 3 Validation (TRICERATOPS+ + SHERLOCK + recovery tests + completeness map), Page 4 Uncertainties (MCMC posteriors + assumptions + limitations)
- [ ] **RPRT-02**: Pipeline outputs candidate catalogue CSV with columns: TIC ID, period, depth, duration, SDE, SNR, classification label, disposition, confidence score, confidence tier, parameter uncertainties
- [ ] **RPRT-03**: Disposition column uses labels: PLANET CANDIDATE, ECLIPSING BINARY, BACKGROUND BLEND, STELLAR VARIABILITY, SUB-THRESHOLD
- [ ] **RPRT-04**: Pipeline runs via single command: `python run_pipeline.py --sectors 1,2,3`

### ML Operations

- [ ] **MLOP-01**: MLflow logs hyperparameters, loss curves, validation metrics, confusion matrices, ECE before/after calibration, and model artifacts per training run
- [ ] **MLOP-02**: MLflow runs stored locally (`.mlruns/`) with two tracked experiments: (1) Kepler CNN pre-training, (2) TESS fine-tuning + XGBoost ensemble

## v2 Requirements

Deferred to post-hackathon. Tracked but not in current roadmap.

- **SCALE-01**: Multi-sector search spanning all 26 TESS sectors (~500k stars)
- **FOLW-01**: Ground-truth follow-up observation planning (observing window computation)
- **ATMO-01**: Transit spectroscopy for atmospheric characterization (H₂O, CO₂, CH₄)
- **AUTH-01**: Dashboard user authentication and manual disposition override capability
- **STRE-01**: Real-time streaming data processing pipeline
- **FFI-01**: TESS Full Frame Image (30-min cadence) support for broader stellar survey beyond 2-min cadence targets
- **HPC-01**: Multi-GPU distributed training for larger ensemble architectures
- **LIVE-01**: Live Python backend for on-demand reprocessing from dashboard

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time streaming data processing | Offline batch pipeline sufficient; TESS data is archive access. Not in evaluation criteria. |
| Full atmospheric characterization | Transit spectroscopy requires different analysis methods and weeks of work. Mention as future work. |
| Training large transformers from scratch | Bi-LSTM + Transformer would need > 4 hours on T4; Dual-View CNN is peer-reviewed, faster, and ADR-0001 decided. |
| OAuth / user authentication for dashboard | Read-only static viewer sufficient; auth adds 3+ hours of infrastructure work judges will not test. |
| Custom HDF5 data format | .npz + Parquet chosen per ADR decisions; zero-dependency, per-star isolation. |
| Live Python backend for dashboard | Next.js reads pre-rendered /outputs/ files; no Flask/FastAPI complexity. |
| Binary classification only | Problem statement requires multi-class; 4-class taxonomy canonical. |
| Instrumentals as a 5th classifier class | Non-astrophysical artefacts handled via TESS quality flags preprocessing gate. |
| Interpolating 13-day TESS data gaps | Creates synthetic structure; masking is correct approach. |
| Hard-coded limb darkening coefficients | Per-star interpolation from TICv8 is essentially free and avoids systematic depth error. |
| Using retired VESPA for FPP | Community standard is now TRICERATOPS+ (Giacalone 2021 / Gomez Barrientos 2025). |
| Multi-sector beyond 3 | 3 sectors sufficient for cross-sector validation; scalable claim in pitch only. |
| Training models from scratch during hackathon | All training (Kepler pre-training + TESS fine-tuning) completed during 7-day preparation window. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Done |
| DATA-02 | Phase 1 | Deferred (Phase 2) |
| DATA-03 | Phase 1 | Deferred (Phase 2) |
| DATA-04 | Phase 1 | Deferred (Phase 2) |
| DATA-05 | Phase 1 | Done |
| PREP-01 | Phase 1 | Done |
| PREP-02 | Phase 1 | Done |
| PREP-03 | Phase 1 | Done |
| PREP-04 | Phase 1 | Done |
| PREP-05 | Phase 1 | Done |
| PREP-06 | Phase 1 | Done |
| PREP-07 | Phase 1 | Done |
| DET-01 | Phase 1 | Done |
| DET-02 | Phase 1 | Done |
| DET-03 | Phase 1 | Done |
| DET-04 | Phase 1 | Done |
| DET-05 | Phase 1 | Done |
| FEAT-01 | Phase 2 | Pending |
| FEAT-02 | Phase 2 | Pending |
| FEAT-03 | Phase 2 | Pending |
| FEAT-04 | Phase 2 | Pending |
| CLAS-01 | Phase 2 | Pending |
| CLAS-02 | Phase 2 | Pending |
| CLAS-03 | Phase 2 | Pending |
| CLAS-04 | Phase 2 | Pending |
| CLAS-05 | Phase 2 | Pending |
| CLAS-06 | Phase 2 | Pending |
| CLAS-07 | Phase 2 | Pending |
| CONF-01 | Phase 2 | Pending |
| CONF-02 | Phase 2 | Pending |
| CONF-03 | Phase 2 | Pending |
| PARM-01 | Phase 3 | Complete |
| PARM-02 | Phase 3 | Complete |
| PARM-03 | Phase 3 | Complete |
| PARM-04 | Phase 3 | Complete |
| PARM-05 | Phase 3 | Complete |
| PARM-06 | Phase 3 | Complete |
| VAL-01 | Phase 3 | Complete |
| VAL-02 | Phase 3 | Complete |
| VAL-03 | Phase 3 | Complete |
| VAL-04 | Phase 3 | Complete |
| VAL-05 | Phase 3 | Complete |
| VIS-01 | Phase 3 | Complete |
| VIS-02 | Phase 3 | Complete |
| VIS-03 | Phase 3 | Complete |
| DASH-01 | Phase 4 | Pending |
| DASH-02 | Phase 4 | Pending |
| DASH-03 | Phase 4 | Pending |
| DASH-04 | Phase 4 | Pending |
| RPRT-01 | Phase 4 | Pending |
| RPRT-02 | Phase 4 | Pending |
| RPRT-03 | Phase 4 | Pending |
| RPRT-04 | Phase 4 | Pending |
| MLOP-01 | Phase 2 | Pending |
| MLOP-02 | Phase 2 | Pending |

**Coverage:**

- v1 requirements: 55 total
- Mapped to phases: 55
- Unmapped: 0

---
*Requirements defined: 25 Jun 2026*
*Last updated: 25 Jun 2026 after initial definition*
