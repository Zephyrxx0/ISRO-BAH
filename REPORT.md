# ISRO BAH 2026 PS-07 — Exoplanet Detection Pipeline

## Comprehensive Technical Report

**Version:** 2.6  
**Date:** 01 July 2026  
**Team Size:** 3–4  
**Event:** ISRO Bharatiya Antariksh Hackathon 2026 Grand Finale (6–7 August 2026)

---

## 1. Opportunity

### 1.1 The Problem

NASA's TESS (Transiting Exoplanet Survey Satellite) produces photometric time-series data for millions of stars. Within this ocean of light curves, a genuine exoplanet transit — an ~84 parts-per-million dip caused by an Earth-sized planet crossing its star — is buried under instrumental noise, stellar variability, and a host of astrophysical impostors. Eclipsing binary stars, background blends, and starspot modulations all produce transit-like signals that fool naive detection algorithms.

Mission scientists currently spend hundreds of hours manually vetting each candidate. The ISRO problem statement PS-07 demands an automated pipeline that can: detect transit signals, classify them into four astrophysical classes, estimate orbital parameters with calibrated uncertainties, and present results through a professional interface — all within a 30-hour hackathon.

### 1.2 How This Solution Is Different

| Aspect | Conventional Approaches | This Pipeline |
|--------|------------------------|---------------|
| **Detection Algorithm** | BLS (Box Least Squares) — box-shaped transit model, misses 10–15% of small planets | **TLS (Transit Least Squares)** primary — realistic ingress/egress shape, GPU-accelerated. BLS runs as validation backup. |
| **Classification** | Binary planet/not-planet or rule-based vetting tools | **4-class ML ensemble** — Planet Candidate, Eclipsing Binary, Background Blend, Stellar Variability. Dual-View CNN (AstroNet) combined with XGBoost on 8 engineered physics features. |
| **Training Strategy** | Train from scratch on TESS data (limited labels) | **Kepler pre-training + TESS fine-tuning** — 34,032 labeled TCEs from Kepler DR24 provide a strong morphological prior. Fine-tuning adapts to TESS-specific noise in <2 hours. |
| **Confidence Scores** | Raw softmax probabilities (overconfident, miscalibrated) | **Temperature-scaled ensemble** with ECE < 0.04 target. Gold (>0.90), Silver (0.70–0.90), Bronze (<0.70) tiers. |
| **Parameter Estimation** | Single-fit or MCMC on all candidates | **Two-gate design**: Nelder-Mead batman fit on ~50 promising candidates, full emcee MCMC (32 walkers × 5000 steps) only on top 15 Gold-tier. |
| **False Positive Validation** | Basic metrics or none | **TRICERATOPS+** Bayesian FPP/NFPP on top 5 Gold candidates (community-standard "Validated Planet" thresholds). **SHERLOCK** independent benchmark comparison (98% TOI recovery rate). |
| **Dashboard** | CSV + static PNGs or Flask/FastAPI live backend | **Pre-rendered Next.js dashboard** — reads static files from `/outputs/`, no live Python server. Interactive celestial star map, AI-powered research synthesis, telemetry terminal. |
| **Aperture Vetting** | Light curve shape only | **Centroid analysis from Target Pixel Files** — flux-weighted centroid shift > 3σ flags background blends at pixel level. |
| **Data Augmentation** | None or basic noise injection | **7× augmentation** including synthetic transit injection (50–200 ppm depths) — addresses shallow-transit underrepresentation and powers completeness map. |

### 1.3 Unique Selling Points

1. **Peer-reviewed architecture lineage**: AstroNet (Shallue & Vanderburg 2018) → ExoMiner++ (Valizadegan 2025) → this pipeline. Every algorithmic choice is backed by published astronomy literature.

2. **Compute-gated design**: Expensive operations are reserved for the most promising candidates. MCMC on 15 stars, not 60,000. GP detrending on 100 stars, not all. Centroid analysis on top 200. This makes the 30-hour window possible.

3. **Calibrated confidence**: Temperature-scaled probabilities with measurable ECE. When the pipeline says "94% confidence," it means correct 94% of the time. Mission planners can trust the triage.

4. **Single command execution**: `python pipeline/run_pipeline.py --sectors 1,2,3 --presentation` produces every output — preprocessed light curves, candidate catalogue, diagnostic plots, PDF report, and dashboard data.

5. **AI-assisted research synthesis**: Each per-star detail page includes a "Generate Report" button that queries the SIMBAD astronomical database via ADQL, pipes the data to Google Gemini, and streams back a professional 2-paragraph astrophysical evaluation in real time.

6. **TLS primary, not BLS**: Detects 10–15% more small planets than the conventional method. This is the difference between finding or missing Earth-sized worlds.

---

## 2. Features

### 2.1 Pipeline Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    ISRO BAH 2026 — EXOPLANET DETECTION PIPELINE            │
│                                                                          │
│  STAGE 0: DATA INGESTION                                                 │
│  ─────────────────────                                                   │
│  MAST API (lightkurve/astroquery) → async HTTP parallel download         │
│  ~60,000 .npz light curve files + TIC stellar parameters (Parquet)       │
│                                                                          │
│  STAGE 1: PREPROCESSING                                                  │
│  ─────────────────────                                                   │
│  Quality mask → sigma-clip (5σ) → normalize → biweight detrend (Wotan)   │
│  Mask 13-day TESS data gaps (no interpolation) | Tmag < 6 filter         │
│  Per-star limb darkening coefficients from TICv8 (Claret & Bloemen 2011) │
│  Two-tier: biweight for all 60k → GP (celerite2) for top 100 candidates  │
│                                                                          │
│  STAGE 2: PERIOD SEARCH                                                  │
│  ────────────────────                                                    │
│  TLS primary: 0.5–30 day periods, 50k frequency steps, 3 iterations     │
│  Multi-planet iterative search with signal masking                       │
│  SDE 3-tier gating: <5 discard | 5–7 sub-threshold | ≥7 full pipeline   │
│  BLS validation on top candidates                                        │
│                                                                          │
│  STAGE 3: FEATURE EXTRACTION                                             │
│  ─────────────────────────                                              │
│  8 engineered features: odd/even depth, secondary eclipse, centroid      │
│  shift, V-shape metric, CROWDSAP, duration/period ratio, SDE, SNR       │
│  Phase folding: 2001-pt global view + 201-pt local zoom (AstroNet spec) │
│  TPF centroid analysis on top 200 candidates for blend detection        │
│                                                                          │
│  STAGE 4: ML CLASSIFICATION                                              │
│  ────────────────────────                                                │
│  ┌─────────────┐     ┌──────────────┐                                   │
│  │ DUAL-VIEW CNN │     │   XGBOOST     │                                  │
│  │ (TensorFlow)  │     │  (sklearn)    │                                  │
│  │ Kepler pre-   │     │  8 features   │                                  │
│  │ trained →      │     │  per candidate│                                  │
│  │ TESS fine-tuned│     │               │                                  │
│  └──────┬───────┘     └───────┬───────┘                                   │
│         └──────┬──────────────┘                                          │
│         ┌──────────────┐                                                 │
│         │   ENSEMBLE    │  0.6 × CNN + 0.4 × XGBoost                     │
│         │   4-class     │  PC / EB / Blend / StellarVar                  │
│         └──────┬───────┘                                                 │
│         ┌──────────────┐                                                 │
│         │ TEMPERATURE   │  ECE < 0.04 | Gold >0.90 / Silver 0.70-0.90   │
│         │   SCALING     │  / Bronze <0.70                                │
│         └──────────────┘                                                 │
│                                                                          │
│  STAGE 5: PARAMETER ESTIMATION                                           │
│  ────────────────────────────                                            │
│  GATE 1: SDE ≥ 7 + PC confidence ≥ 0.70 → batman Nelder-Mead fit        │
│  GATE 2: PC confidence ≥ 0.85 (top 15) → emcee MCMC (32 walkers × 5000) │
│  TOP 5 GOLD: TRICERATOPS+ FPP/NFPP + SHERLOCK benchmark                  │
│                                                                          │
│  STAGE 6: OUTPUT & VISUALIZATION                                         │
│  ──────────────────────────────                                          │
│  4-panel diagnostics (PNG + Plotly HTML) | Corner plots (corner)         │
│  Confusion matrix heatmap | SHAP feature importance | Completeness map   │
│                                                                          │
│  STAGE 7: REPORT & DASHBOARD                                             │
│  ──────────────────────────                                             │
│  Candidate catalogue CSV | 4-page PDF report | Next.js static dashboard  │
│  Pre-rendered from /outputs/ | No live Python backend                    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Complete Feature List

#### A. Data Ingestion (12 features)

| # | Feature | Description |
|---|---------|-------------|
| A1 | **TESS Sector Download** | Downloads TESS 2-min cadence light curves for Sectors 1, 2, 3 (~60,000 stars) from MAST via lightkurve/astroquery with async parallel HTTP (4× speed) |
| A2 | **Target Pixel File Download** | Downloads TPFs via TESScut for centroid analysis on top SDE ≥ 7 candidates |
| A3 | **ExoFOP-TESS Label Acquisition** | Downloads TOI disposition table from ExoFOP-TESS for classifier training labels |
| A4 | **Kepler DR24 Ingest** | Downloads 34,032 labeled TCEs from Kepler DR24 catalogue for CNN pre-training |
| A5 | **TICv8 Stellar Parameters** | Queries TICv8 catalogue for stellar parameters (Teff, logg, Rs, Ms, Tmag, CROWDSAP, RA, Dec) |
| A6 | **Limb Darkening Tables** | Downloads Claret & Bloemen (2011) quadratic limb darkening coefficient tables |
| A7 | **Per-Star .npz Storage** | Stores each light curve as an independent .npz file (zero-dependency, corruption isolation) |
| A8 | **Parquet Master Catalogue** | Maintains a columnar Parquet master catalogue of all stars, candidates, and pipeline outputs |
| A9 | **Kaggle Environment Detection** | Auto-detects Kaggle vs. local environments and sets appropriate paths |
| A10 | **Sector-Aware File Organization** | Organizes raw and preprocessed data by sector (`raw/`, `preprocessed/`) |
| A11 | **MAST TIC Query** | Programmatic TIC catalogue querying via astroquery MAST Catalogs API |
| A12 | **Pre-Hackathon Data Caching** | Supports pre-downloading Sector 1 data to avoid MAST rate-limiting during event |

#### B. Preprocessing (9 features)

| # | Feature | Description |
|---|---------|-------------|
| B1 | **TESS Quality Flag Masking** | Removes cadences flagged as AttitudeTweak, SafeMode, CosmicRay, ManualExclude |
| B2 | **Sigma Clipping** | 5σ iterative sigma clipping to remove outliers while preserving transit depths |
| B3 | **Flux Normalization** | Normalizes flux to median = 1.0 for consistent transit depth measurement |
| B4 | **Biweight Detrending** | Wotan biweight detrending with window_length ≥ 0.75 days — 500× faster than GP, preserves transit shapes |
| B5 | **Gaussian Process Detrending** | celerite2 Matérn-3/2 kernel GP on top 100 SDE ≥ 7 candidates for correlated (red) noise modeling |
| B6 | **13-Day Data Gap Masking** | Masks (does not interpolate) TESS's ~13-day data gaps to prevent false periodic signal detection |
| B7 | **Gap-Edge Flagging** | Flags cadences within ±0.5 days of gap boundaries as unreliable |
| B8 | **Star Quality Filters** | Excludes stars with Tmag < 6 (saturation artefacts) and light curves with < 500 valid cadences |
| B9 | **Per-Star Limb Darkening** | Interpolates quadratic limb darkening coefficients from TICv8 using Claret & Bloemen tables — avoids systematic depth error from hard-coded defaults |

#### C. Detection — Period Search (7 features)

| # | Feature | Description |
|---|---------|-------------|
| C1 | **TLS Primary Period Search** | Transit Least Squares as primary detection algorithm — 10–15% more small-planet detections than BLS, physically motivated transit shape model |
| C2 | **50k Frequency Steps** | Period range 0.5–30 days with 50,000 frequency steps and 2× oversampling |
| C3 | **Multi-Planet Iterative Search** | 3 iterations of signal detection, masking, and re-running TLS — critical for systems like TOI-270 (3 planets) |
| C4 | **BLS Validation** | Box Least Squares run as independent validation on top candidates, cross-checking TLS results |
| C5 | **3-Tier SDE Gating** | SDE < 5 → discard, 5 ≤ SDE < 7 → sub-threshold inventory, SDE ≥ 7 → full pipeline |
| C6 | **Signal Metrics Computation** | Computes SDE (Signal Detection Efficiency), SNR, and CDPP for every detected signal |
| C7 | **Batch TLS Processing** | GPU-accelerated batch TLS search with configurable worker parallelism |

#### D. Feature Extraction (8 features)

| # | Feature | Description |
|---|---------|-------------|
| D1 | **Odd/Even Depth Difference** | Compares transit depths in odd vs. even transits — EBs show alternating depths, planets show equal depths |
| D2 | **Secondary Eclipse Detection** | Measures flux dip at orbital phase 0.5 — present in EBs, absent in planets |
| D3 | **Centroid Shift Analysis** | Flux-weighted centroid position during transit vs. out-of-transit from TPF data — shift > 3σ indicates background blend |
| D4 | **V-Shape Metric** | Ratio of ingress+egress duration to total transit — V-shaped suggests grazing EB, flat-bottom suggests planet |
| D5 | **CROWDSAP Pre-Filter** | Contamination ratio from TICv8 — blocks PC classification if > 0.5, flags centroid investigation if > 0.3 |
| D6 | **Duration/Period Ratio** | Transit duration relative to orbital period — discriminates stellar density effects |
| D7 | **Phase Folding (AstroNet)** | 2001-point global view + 201-point local zoom view — the canonical input format for the Dual-View CNN |
| D8 | **Feature Validation Against Published Planets** | Cross-validates extracted features against known exoplanet parameters |

#### E. ML Classification (12 features)

| # | Feature | Description |
|---|---------|-------------|
| E1 | **Dual-View CNN (AstroNet)** | 6 Conv1D layers (global tower) + 4 Conv1D layers (local tower) → merged dense head with 4-class softmax output |
| E2 | **Kepler DR24 Pre-Training** | CNN trained on 34,032 labeled Kepler TCEs before hackathon — provides strong transit morphology prior |
| E3 | **TESS ExoFOP Fine-Tuning** | Fine-tunes Kepler-pre-trained CNN on TESS TOI labels with reduced learning rate — adapts to TESS-specific noise |
| E4 | **XGBoost Classifier** | Gradient-boosted trees on 8 engineered features with stratified 5-fold cross-validation and F1-macro optimization |
| E5 | **Ensemble (0.6×CNN + 0.4×XGBoost)** | Weighted softmax averaging in log-space for numerical stability — combines deep learning shape recognition with physics-based feature discrimination |
| E6 | **7× Data Augmentation** | Noise injection, transit-time jitter, flux scaling, phase-folding jitter, and synthetic transit injection — 85k effective training samples |
| E7 | **Synthetic Transit Injection** | batman-model transits at 50–2000 ppm injected into real detrended TESS noise — addresses shallow-transit underrepresentation |
| E8 | **Completeness Map** | Recovery fraction as function of transit depth and orbital period from synthetic injection results |
| E9 | **Temperature Scaling** | Post-hoc calibration dividing logits by learned temperature parameter T — aligns predicted confidence with empirical accuracy |
| E10 | **ECE (Expected Calibration Error)** | Weighted average difference between predicted confidence and observed accuracy — target < 0.04 |
| E11 | **Gold/Silver/Bronze Tiers** | Gold > 0.90, Silver 0.70–0.90, Bronze < 0.70 — mission-planner triage bands |
| E12 | **CROWDSAP Classification Gate** | Candidates with CROWDSAP > 0.5 cannot be classified as Planet Candidate regardless of model output |

#### F. Model Evaluation & Explainability (4 features)

| # | Feature | Description |
|---|---------|-------------|
| F1 | **Confusion Matrix** | Per-class precision, recall, F1, ROC-AUC (one-vs-rest) with heatmap visualization |
| F2 | **SHAP Feature Importance** | TreeExplainer on XGBoost — per-feature importance summary plot showing which physics features drive each classification |
| F3 | **Reliability Diagram** | Calibration curve plotting predicted probability vs. observed accuracy across confidence bins |
| F4 | **MLflow Experiment Tracking** | Logs hyperparameters, loss curves, validation metrics, confusion matrices, ECE, and model artifacts per training run |

#### G. Parameter Estimation (8 features)

| # | Feature | Description |
|---|---------|-------------|
| G1 | **Nelder-Mead batman Fit** | First gate — scipy Nelder-Mead optimization of Mandel-Agol transit model for SDE ≥ 7 + PC confidence ≥ 0.70 candidates (~50 stars) |
| G2 | **emcee MCMC Sampling** | Second gate — 32 walkers × 5000 steps on top 15 Gold candidates (PC confidence ≥ 0.85). Full Bayesian posterior. |
| G3 | **HDF5 Checkpointing** | MCMC chains saved incrementally via HDF5 backend — crash recovery without re-running |
| G4 | **Convergence Diagnostics** | Acceptance fraction 0.2–0.5 validation, autocorrelation time check, Gelman-Rubin diagnostic |
| G5 | **MCMC Fallback** | Non-converging chains fall back to Nelder-Mead fit; flagged as "parameters uncertain" |
| G6 | **Corner Plots** | 2D posterior distributions with 1σ/2σ contours per MCMC candidate using the corner package |
| G7 | **Parameter Reporting** | Median ± 1σ (16th/84th percentile credible intervals) for P, T₁₄, δ, Rp/Rs, inclination |
| G8 | **Parameter Recovery Validation** | Period within 0.1% for SNR > 10, depth within 5%, duration within 10% against published values |

#### H. Validation & Vetting (7 features)

| # | Feature | Description |
|---|---------|-------------|
| H1 | **TRICERATOPS+ FPP** | Bayesian False Positive Probability on top 5 Gold planet candidates — FPP < 1.5% qualifies as Validated Planet |
| H2 | **TRICERATOPS+ NFPP** | Nearby False Positive Probability — NFPP < 0.1% alongside FPP < 1.5% for validation |
| H3 | **TRICERATOPS Mode Breakdown** | Decomposes FPP into TP, EB, HEB, BGOB probability modes |
| H4 | **SHERLOCK Benchmark** | Independent recovery check against SHERLOCK pipeline (98% TOI recovery rate) on top 5 candidates |
| H5 | **Known Planet Recovery Tests** | Pre-pipeline validation on WASP-121b (Sector 1), TOI-270 (3 planets, Sector 3), L 98-59 (3 planets, Sector 2), TOI-700 d |
| H6 | **Smoke Test Suite** | Automated 7-benchmark-planet recovery verification |
| H7 | **Published Parameter Cross-Reference** | Validates estimated parameters against published values from NASA Exoplanet Archive |

#### I. Visualization (5 features)

| # | Feature | Description |
|---|---------|-------------|
| I1 | **4-Panel Diagnostic Plot** | (1) Raw+detrended LC with transit markers, (2) TLS periodogram with peak annotation, (3) Phase-folded LC + batman model + residuals, (4) Classifier softmax bar chart |
| I2 | **Dual-Format Export** | Publication-quality PNG (150 dpi) + interactive Plotly HTML per candidate |
| I3 | **Completeness Map** | Recovery fraction as function of transit depth (50–2000 ppm) and orbital period |
| I4 | **Phase-Folded Flux Profile** | Raw TESS data points overlaid with transit model fit (Plotly) — the core astronomical visualization |
| I5 | **Pipeline Flowchart** | Auto-generated pipeline architecture diagram for PDF report |

#### J. Interactive Dashboard (13 features)

| # | Feature | Description |
|---|---------|-------------|
| J1 | **Candidate Table** | Filterable (by TIC ID + confidence tier), sortable, paginated (20 rows/page) table using @tanstack/react-table |
| J2 | **Confidence Tier Filters** | One-click filter: All, Gold, Silver, Bronze, False Positive |
| J3 | **Per-Star Detail Page** | Dynamic route `/star/[ticid]` with full diagnostic view, validation report, and AI synthesis |
| J4 | **4-Panel Diagnostic Tab** | Raw-detrended LC, TLS periodogram, phase-folded + model, classifier softmax — inline Plotly rendering |
| J5 | **MCMC Corner Plot Display** | Full posterior distribution corner plot for Gold-tier candidates |
| J6 | **Validation Engine Display** | TRICERATOPS+ FPP/NFPP progress bars + mode breakdown + SHERLOCK pass/fail matrix with sector-by-sector detail |
| J7 | **Transit Fit Matrix** | Phase-folded flux profile with raw data points, model fit overlay, and telemetry sidebar (period, depth, duration, SDE, SNR, tier) |
| J8 | **Simulation Panel** | Pipeline control simulation (H00 Baseline vs. H18 Inference) with terminal-style log buffer showing processing stages |
| J9 | **Celestial Star Map** | Interactive Leaflet.js sky map with RA/Dec coordinate projection, zoom controls, candidate markers, and telemetry info panel |
| J10 | **Celestial Grid** | RA/Dec grid overlay with J2000.0 coordinate system reference |
| J11 | **AI Synthesis Panel** | On-demand AI research report generation — queries SIMBAD via ADQL, pipes data to Google Gemini (gemini-2.5-flash-lite), streams 2-paragraph evaluation |
| J12 | **Summary Statistics** | Dashboard header with Total Candidates, Gold Tier count, Confirmed Planets, Average SDE |
| J13 | **Breadcrumb Navigation** | Contextual navigation trail: HOME // TIC_ID with monospace terminal styling |

#### K. Report & Deliverables (5 features)

| # | Feature | Description |
|---|---------|-------------|
| K1 | **4-Page PDF Report** | Page 1 Methodology (flowchart + confusion matrix), Page 2 Results (candidate table + best planet), Page 3 Validation (TRICERATOPS+ FPP + SHERLOCK + recovery tests + completeness), Page 4 Uncertainties (MCMC posteriors + assumptions + limitations) |
| K2 | **Candidate Catalogue CSV** | TIC ID, period, depth, duration, SDE, SNR, classification, disposition, confidence score, confidence tier, parameter uncertainties |
| K3 | **Dashboard JSON Generation** | Generates `candidates.json` (all SDE ≥ 5) and per-star JSON files (SDE ≥ 7) for Next.js static build |
| K4 | **Pipeline-to-Dashboard Sync** | Copies plots and JSON outputs to SPACE/ directory automatically |
| K5 | **Single-Command Execution** | `python pipeline/run_pipeline.py --sectors 1,2,3 --presentation` runs entire pipeline |

#### L. AI-Assisted Research (undocumented feature — new)

| # | Feature | Description |
|---|---------|-------------|
| L1 | **SIMBAD ADQL Query** | Queries the SIMBAD astronomical database via TAP endpoint using ADQL — retrieves Main ID, RA, Dec, and Spectral Type for any TIC ID |
| L2 | **Gemini AI Synthesis** | Sends pipeline metrics (SDE, FPP, disposition) + SIMBAD context to Google Gemini 2.5 Flash Lite for professional research evaluation |
| L3 | **Streaming Response** | AI report streams real-time via SSE (Server-Sent Events) with `text/event-stream` content type |
| L4 | **Markdown Rendering** | AI-generated report rendered as rich Markdown with `react-markdown` — supports images, formatting, and structured text |
| L5 | **Guardrail Prompts** | Explicit guardrails prevent data hallucination — "Do NOT hallucinate data. Stick only to the data provided above." |

#### M. Architecture & Engineering (8 features)

| # | Feature | Description |
|---|---------|-------------|
| M1 | **Pre-Rendered Static Dashboard** | Python pipeline pre-renders all visuals; Next.js reads from `/outputs/` — no live Python server at demo time |
| M2 | **Integration Schema Contract** | TypeScript schema (`integration-schema.ts`) defining PipelinePayload, CandidateEntry, AstronomicalSignal, LightCurveData, TriceratopsValidation, SherlockValidation |
| M3 | **Mock Data Generator** | Generates realistic mock payload data for dashboard development without pipeline outputs |
| M4 | **Makefile Orchestration** | `make pipeline`, `make dashboard`, `make serve`, `make clean`, `make dev` |
| M5 | **Modular Package Structure** | Clean separation: `pipeline/` (orchestration), `src/phase2/` (ML), `src/characterization/` (parameters), `src/report/` (outputs), `src/visualization/` (plots), `src/validation/` (benchmarks) |
| M6 | **Comprehensive Test Suite** | 22 pytest test files covering all pipeline modules with `conftest.py` fixtures |
| M7 | **Jupyter Notebooks** | Interactive notebooks for Kepler pre-training (kaggle_kepler_pretrain), TESS fine-tuning (kaggle_tess_finetune), preprocessing (nb04), TLS search (nb05), and Kepler download (nb06) |
| M8 | **Phase 2 Verification Scripts** | Shell and PowerShell verification runners (`verify_phase2.sh`, `verify_phase2.ps1`) |

---

## 3. Technologies

### 3.1 Python Pipeline Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Language** | Python | 3.10+ | Entire astronomy ecosystem is Python-native |
| **Data Access** | lightkurve | 2.x | NASA official TESS/Kepler library — data download, manipulation, BLS |
| **Data Access** | astroquery | 0.4.x | Programmatic MAST access, TIC catalogue queries, TESScut TPF downloads |
| **Astronomy Core** | astropy | 6.x | FITS I/O, coordinate transforms, units, BLS periodogram |
| **Detection** | transitleastsquares (TLS) | 1.x | Primary period search — 10–15% better small-planet detection than BLS |
| **Detrending** | wotan | 1.x | Biweight detrending — 500× faster than GP, preserves transit shapes |
| **GP Modeling** | celerite2 | 0.4.x | Matérn-3/2 Gaussian Process for correlated noise on top candidates |
| **Transit Model** | batman-package | 2.x | Mandel-Agol analytic transit light curve model |
| **MCMC** | emcee | 3.x | Ensemble MCMC sampler — 32 walkers, HDF5 checkpointing |
| **Corner Plots** | corner | 2.x | Publication-quality 2D posterior distribution visualization |
| **Deep Learning** | TensorFlow / Keras | 2.x | Dual-View CNN (AstroNet architecture) — Kepler pre-training + TESS fine-tuning |
| **ML** | XGBoost | 2.x | Gradient-boosted tree classifier on engineered features |
| **ML** | scikit-learn | 1.5.x | Train/test split, stratified k-fold, classification metrics |
| **Explainability** | SHAP | 0.46.x | TreeExplainer — per-feature importance for XGBoost |
| **Calibration** | scikit-learn (post-hoc) | — | Temperature scaling implementation |
| **Numerical** | NumPy | 1.26+ | Array computation, .npz I/O |
| **Scientific** | SciPy | 1.14+ | Nelder-Mead optimization, signal processing, statistics |
| **DataFrames** | Pandas | 2.x | Parquet I/O, catalogue management, CSV export |
| **Tracking** | MLflow | 2.x | Experiment tracking, model versioning, auto-logging |
| **Visualization** | Matplotlib | 3.9.x | Publication-quality static plots, PDF report figures |
| **Interactive** | Plotly | 5.x | Interactive HTML diagnostic plots for dashboard |
| **Statistics** | Seaborn | 0.13.x | Confusion matrix heatmaps |
| **Progress** | tqdm | 4.x | Progress bars for bulk processing |
| **PDF** | fpdf2 | 2.7.x | 4-page PDF report generation |
| **Archive** | pyvo | 1.5.x | NASA Exoplanet Archive queries for validation targets |

### 3.2 Next.js Dashboard Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Framework** | Next.js | 16.2.9 | App Router, static export, dynamic routes |
| **UI Library** | React | 19.2.4 | Component architecture |
| **Styling** | Tailwind CSS | 4.x | Utility-first CSS with custom design tokens |
| **Components** | shadcn/ui | 4.12.0 | Table, Card, Badge, Button, Tabs, Input, Select primitives |
| **Table** | @tanstack/react-table | 8.21.3 | Sortable, filterable, paginated data tables |
| **Charts** | Plotly.js (dist-min) | 3.6.0 | Client-side interactive diagnostic plots |
| **Maps** | Leaflet + react-leaflet | 1.9.4 | Celestial star map with CRS.Simple projection |
| **AI** | @google/generative-ai | 0.24.1 | Gemini 2.5 Flash Lite integration |
| **Markdown** | react-markdown | 10.1.0 | AI synthesis report rendering |
| **Icons** | lucide-react | 1.21.0 | Sparkles, AlertCircle icons |
| **Utilities** | clsx, class-variance-authority, tailwind-merge | — | CSS class composition |
| **Types** | TypeScript | 5.x | Type safety for integration schema and components |

### 3.3 Infrastructure & DevOps

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Environment** | Python venv | Isolated Python dependencies |
| **Package Manager** | pnpm | TypeScript dependency management |
| **Build** | Makefile | Top-level orchestration: `pipeline`, `dashboard`, `serve`, `clean`, `dev` |
| **GPU** | NVIDIA T4 (Colab free tier) | Model training — mixed precision, batch size 32 |
| **Storage** | .npz + Parquet | Per-star light curves + columnar catalogue (no HDF5, no PostgreSQL) |
| **Notebooks** | Jupyter | Interactive exploration and Kaggle notebook exports |
| **Testing** | pytest | 22 test modules with fixture-based test setup |
| **Version Control** | Git | Feature branches per phase |
| **External API** | SIMBAD TAP | ADQL queries for stellar identification |
| **External API** | Google Gemini | AI-powered research synthesis |

---

## 4. Estimated Implementation Cost

| Component | Effort (Person-Hours) | Rationale |
|-----------|----------------------|-----------|
| **Data Ingestion** | 8 | lightkurve/astroquery pipeline with async download, MAST auth, TIC queries |
| **Preprocessing Pipeline** | 12 | Biweight detrending, quality masking, gap handling, limb darkening, GP detrending |
| **TLS Period Search** | 10 | GPU-accelerated batch TLS, multi-planet iterative removal, BLS validation |
| **Feature Extraction** | 10 | 8 engineered features, phase folding, TPF centroid analysis |
| **CNN Architecture + Training** | 16 | AstroNet Dual-View implementation, Kepler pre-training (3–4h GPU), TESS fine-tuning |
| **XGBoost + Ensemble** | 8 | Feature-based classifier training, weighted ensemble, temperature scaling |
| **Synthetic Transit Injection** | 8 | batman model injection, augmentation pipeline, completeness map |
| **Parameter Estimation** | 12 | Nelder-Mead batman fit, emcee MCMC, convergence diagnostics, corner plots |
| **Validation & Vetting** | 10 | TRICERATOPS+ integration, SHERLOCK benchmark, known planet recovery tests |
| **Visualization** | 8 | 4-panel diagnostics, Plotly HTML exports, confusion matrix, SHAP plots |
| **Next.js Dashboard** | 20 | Candidate table, per-star pages, celestial map, AI synthesis, validation engine |
| **PDF Report** | 6 | 4-page fpdf2/matplotlib report with embedded plots |
| **Testing & QA** | 10 | 22 test files, smoke tests, schema validation |
| **Integration & DevOps** | 6 | Makefile, schema contracts, pipeline-to-dashboard sync |
| **Documentation** | 6 | ADRs, planning docs, research docs, AGENTS.md, CONTEXT.md |
| **Total** | **~150 person-hours** | Across 4 phases, achievable in 30-hour hackathon with 3–4 members + 7-day prep |

### Cost Breakdown (INR)

| Category | Item | Estimated Cost (INR) |
|----------|------|----------------------|
| **Compute** | NVIDIA T4 GPU (Colab Pro+ / Kaggle) | ₹0 (free tier) |
| **Data** | TESS/MAST archives | ₹0 (public domain) |
| **Cloud** | Vercel hosting (dashboard) | ₹0 (hobby tier, static export) |
| **APIs** | Google Gemini API | ₹0–500 (free tier sufficient, ~50 synthesis calls) |
| **APIs** | SIMBAD TAP | ₹0 (public service) |
| **Software** | All libraries open-source | ₹0 |
| **Team** | 3–4 student members × 30h | Opportunity cost only |
| **Total Out-of-Pocket** | | **~₹0–500** |

The pipeline is designed to run entirely on free-tier infrastructure — Kaggle/Colab T4 GPU, Vercel hobby tier, and public astronomical archives. The only potential cost is minimal Gemini API usage for the AI synthesis feature (~₹0.02 per query).

---

## 5. Domain Glossary

For reference, the project uses 35 canonical domain terms across 6 clusters (from `CONTEXT.md`):

**Observational Data**: Light Curve, Cadence, Sector, TIC (TESS Input Catalog), Target Pixel File

**Signals**: Transit, Transit Depth (δ), Transit Duration (T₁₄), Orbital Period (P), Phase Folding, Periodogram, Secondary Eclipse, Odd/Even Depth Difference, V-Shape Metric

**Signal Classes**: Planet Candidate (PC), Eclipsing Binary (EB), Background Blend, False Positive (FP), Stellar Variability, Instrumental/Systematic, TOI (TESS Object of Interest), Disposition

**Detection Metrics**: SDE (Signal Detection Efficiency), SNR, CDPP (Combined Differential Photometric Precision)

**Classification Metrics**: Confidence Score, Confidence Tier (Gold/Silver/Bronze), ECE (Expected Calibration Error), Temperature Scaling, FPP (False Positive Probability), NFPP (Nearby False Positive Probability), Completeness Map

**Stellar & Training**: CROWDSAP/Contamination Ratio, Centroid Shift, Limb Darkening, Detrending, Posterior Distribution, Pre-training, Fine-tuning, Synthetic Transit Injection, Ensemble

---

## 6. Architecture Decision Records

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-0001 | Dual-View CNN over Bi-LSTM+Transformer | Peer-reviewed (Shallue & Vanderburg 2018), faster training, simpler API |
| ADR-0002 | 3 sectors (1, 2, 3) over single sector | Extended period range, cross-sector validation, fits prep window |
| ADR-0003 | 7× augmentation + synthetic transit injection | Addresses shallow-transit gap, produces completeness map |
| ADR-0004 | Kepler pre-training + TESS fine-tuning | 34k extra samples, strong shape prior, domain adaptation |

---

*This report was generated from the living planning documents in `.planning/`, architecture decision records in `docs/adr/`, and the actual implemented codebase across `pipeline/`, `src/`, `SPACE/`, and `tests/`.*
