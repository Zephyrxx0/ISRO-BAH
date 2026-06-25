# Project Research Summary

**Project:** ISRO BAH 2026 PS-07 — Exoplanet Detection Pipeline
**Domain:** AI-enabled exoplanet detection from TESS transit photometry (30-hour hackathon)
**Researched:** 25 Jun 2026
**Confidence:** HIGH

## Executive Summary

This is an **end-to-end ML pipeline** that ingests TESS satellite photometry (2-minute cadence from 3 sectors, ~60,000 stars), detects periodic transit signals, classifies them into a 4-class taxonomy (Planet Candidate, Eclipsing Binary, Background Blend, Stellar Variability), estimates orbital parameters with Bayesian uncertainties, and presents results through calibrated confidence scores and an interactive dashboard. The project is constrained to a **30-hour hackathon grand finale** judged by ISRO scientists, requiring both scientific rigor and time-efficiency.

The recommended approach is a **7-stage batch pipeline with a pre-rendered static frontend**. Research converges on: TLS (Transit Least Squares) as the primary detection algorithm — it recovers 10–15% more small planets than BLS; a **Dual-View CNN + XGBoost ensemble** (0.6×CNN, 0.4×XGBoost) for 4-class classification, following the AstroNet and ExoMiner++ lineage; **pre-training the CNN on Kepler DR24** (34k labeled TCEs) before the hackathon, then fine-tuning on TESS ExoFOP TOIs during the event; and a **two-gate parameter estimation** design where cheap Nelder-Mead batman fits gate expensive emcee MCMC sampling, keeping MCMC runs to ~15 candidates. The Next.js dashboard reads pre-rendered PNG/HTML/JSON from `/outputs/` — no live Python backend needed at demo time, eliminating deployment risk.

**Key risks center on three areas**: (1) Over-flattening transit signals during detrending — mitigated by a minimum biweight window of 0.75 days and synthetic transit injection validation; (2) MCMC non-convergence producing misleading parameter uncertainties — mitigated by the two-gate design, Nelder-Mead initialization, and convergence diagnostics; (3) Uncalibrated confidence scores creating overconfident false positives — mitigated by post-hoc temperature scaling targeting ECE < 0.04. The pipeline's success depends as much on knowing when to *gate* expensive operations (MCMC only on top 15, GP detrending only on top 100, centroid analysis only on top 200) as on the algorithms themselves.

## Key Findings

### Recommended Stack

The pipeline is **Python-first** (3.10+) for all astronomy and ML work, with **Next.js 14+ (TypeScript)** for the read-only dashboard. All core astronomy libraries are community-standard and peer-reviewed: `lightkurve` for TESS data access, `transitleastsquares` (TLS) for period search, `wotan` for bulk detrending (biweight, ~500× faster than GP), `batman-package` for transit modeling, and `emcee` for MCMC. The ML stack uses **TensorFlow/Keras** (not PyTorch) for the CNN because AstroNet's reference implementation is in TF and Keras offers a simpler API for CNN pipelines, plus **XGBoost** for feature-based classification. Data flows through per-star `.npz` files (corruption isolation) and a master `Parquet` catalog (columnar querying). The dashboard uses **pre-rendered static exports** — Plotly HTML for interactive light curves, leaflet/react-leaflet for the celestial star map, and @shadcn/ui components for the candidate table. No Flask/FastAPI live backend.

**Core technologies:**
- **Python 3.10+** — universal astronomy ecosystem language; every library is Python-native
- **lightkurve + astroquery** — official NASA TESS data access; handles MAST auth, FITS I/O, async parallel download
- **transitleastsquares (TLS)** — primary period search; 10–15% more small-planet detections than BLS; physically motivated transit shape model
- **TensorFlow/Keras** — CNN classifier; AstroNet peer-reviewed architecture; simpler than PyTorch for CNN pipelines
- **XGBoost + SHAP** — feature-based classifier with per-feature explainability; complements CNN's shape recognition
- **batman + emcee** — industry-standard transit model + MCMC; publication-quality posterior distributions
- **Next.js 14+ (static export)** — pre-rendered dashboard; eliminates backend deployment risk; reads from `/outputs/`
- **mlflow** — experiment tracking and reproducibility; auto-logs hyperparameters/metrics/models

### Expected Features

**Must have (table stakes — missing any = incomplete submission):**
- TESS data ingestion from MAST (3 sectors, ~60k targets) — foundational prerequisite
- Light curve preprocessing pipeline (biweight detrending, quality masking, normalization) — gates all downstream stages
- TLS period search with SDE/SNR reporting — core detection engine
- 4-class classifier (PC, EB, Blend, Other FP) — explicitly required by problem statement; binary classification fails
- Engineered feature extraction (8+ features: odd/even depth, secondary eclipse, centroid shift, V-shape, CROWDSAP, etc.)
- Parameter estimation (P, T₁₄, δ) with uncertainties — evaluation criterion for precision
- Temperature-scaled confidence scores with Gold/Silver/Bronze tiers — required for mission planner triage
- Phase-folded 4-panel diagnostic visualizations — judges must see the transit signal is real
- Candidate catalogue CSV — required deliverable; one row per candidate
- Validation on known targets (WASP-121b, TOI-270, L 98-59) — proves pipeline works
- Confusion matrix + classification metrics — quantitative evaluation rigor
- 4-page PDF report — required deliverable mapping to 4 evaluation criteria
- End-to-end single-command execution — `python run_pipeline.py --sectors 1,2,3`

**Should have (differentiators — separate from average submissions):**
- CNN + XGBoost ensemble (weighted softmax) — combines shape recognition with physics priors
- Kepler pre-training + TESS fine-tuning — transfer learning sophistication; saves 2+ hours of training
- MCMC parameter estimation (batman + emcee) on top 15 Gold candidates — full Bayesian posteriors
- Synthetic transit injection + completeness map — direct evidence of pipeline sensitivity
- Multi-planet iterative search and removal — critical for TOI-270/L 98-59 validation
- SHAP feature importance — XAI; shows judges *why* each classification was made
- TRICERATOPS+ FPP/NFPP on top 5 Gold candidates — community-standard Bayesian false positive probability
- SHERLOCK benchmark comparison — third-party credibility
- Interactive Next.js dashboard with celestial star map — memorable, interactive, no other team will have this
- MLflow experiment tracking — professional ML engineering signal
- 7× data augmentation (noise, jitter, rescaling, synthetic injection) — addresses shallow-transit underrepresentation
- Centroid shift analysis from TPF data — pixel-level vetting for blend discrimination

**Defer (v2+ / post-hackathon):**
- Scale to all 26 TESS sectors — pipeline designed for 3; scalability claim for pitch only
- Full atmospheric characterization — completely different domain (transit spectroscopy)
- Real-time streaming / alert system — batch only; streaming infrastructure not in scope
- Large transformer from scratch — Bi-LSTM+Transformer too risky for 30-hour window; CNN is peer-reviewed and faster
- OAuth/authentication for dashboard — read-only static viewer is sufficient
- Extension to Roman Space Telescope data — 2026+ data format, pitch-only

### Architecture Approach

The pipeline follows a **7-stage linear batch architecture** with clearly bounded components, each writing to well-defined file formats. The key design philosophy is **compute gating**: expensive operations are reserved for the highest-confidence candidates, not applied uniformly. Stage 0 (Data Ingestion) downloads TESS FITS via async HTTP → Stage 1 (Preprocessing) applies quality masks, normalization, and biweight detrending → Stage 2 (Period Search) runs TLS on all targets with multi-planet iterative removal → Stage 3 (Feature Extraction) computes 8+ engineered features and phase-folds light curves → Stage 4 (ML Classification) runs the CNN+XGBoost ensemble with temperature-scaled calibration → Stage 5 (Parameter Estimation) applies the two-gate design (Nelder-Mead gate → MCMC gate → TRICERATOPS+ gate) → Stage 6 (Output & Visualization) generates 4-panel diagnostics and summary plots → Stage 7 (Report & Dashboard) produces the candidate CSV, PDF, and pre-rendered dashboard assets.

**Major components:**
1. **Data Ingestor** — Downloads TESS 2-min cadence FITS from MAST for 3 sectors; stores per-star `.npz` + TIC parameters as Parquet
2. **Preprocessor** — Quality-masks, normalizes, biweight-detrends; discards invalid LCs (Tmag < 6, < 500 cadences); masks data gaps
3. **Period Searcher** — TLS on all targets (0.5–30 day, 50k freq steps); iterative multi-planet removal; BLS validation on top candidates
4. **Feature Extractor** — Computes 8+ engineered features; phase-folds light curves (201-pt global + 61-pt local views); downloads TPFs for centroid analysis
5. **CNN Trainer** — Dual-View 1D CNN; Kepler pre-trained weights; fine-tunes on TESS ExoFOP TOIs; 7× data augmentation
6. **XGBoost Trainer** — Gradient boosted trees on engineered features; stratified k-fold (k=5); F1-macro optimization
7. **Ensemble Classifier** — Weighted softmax average (0.6×CNN + 0.4×XGBoost); 4-class output; temperature scaling for calibration
8. **Parameter Estimator** — Two-gate: Nelder-Mead batman fit → MCMC emcee (32 walkers, 5000 steps); TRICERATOPS+ FPP on top 5 Gold
9. **Output Generator** — 4-panel diagnostics (PNG + Plotly HTML); corner plots; confusion matrix; SHAP summary; candidate catalogue CSV; PDF report
10. **Next.js Dashboard** — Read-only static viewer; candidate table with filters; per-star diagnostics modal; celestial star map (RA/Dec via leaflet)

**Key architectural patterns:**
- **Two-Gate Parameter Estimation** — Cheap analytic fit (Nelder-Mead) gates expensive MCMC; prevents hours of wasted compute on false positives
- **Pre-Rendered Static Frontend** — Pipeline pre-renders all visuals; Next.js reads static files; no live Python server at demo time
- **Ensemble with Weighted Softmax Averaging** — CNN learns transit morphology; XGBoost learns physics discriminators; complementary signals
- **Pre-Training + Fine-Tuning Transfer Learning** — Kepler DR24 (34k TCEs) provides strong shape prior; TESS fine-tuning adapts to instrument-specific noise

### Critical Pitfalls

1. **Over-Flattening the Light Curve** — Aggressive detrending (window < 0.75 days) erases transit signals along with stellar variability. **Prevent by:** setting biweight `window_length ≥ 0.75` days (≥ 3× max transit duration); validate with synthetic transit injection; verify WASP-121b detection post-detrending.

2. **Data Gap Interpolation Creating False Signals** — Interpolating across TESS's ~13-day data gaps creates synthetic structure that TLS may detect as periodic signals, inflating false positives 5–10×. **Prevent by:** masking (not interpolating) all data gaps; flagging gap-edge points; discarding LCs with < 500 valid cadences.

3. **Binary Classification Instead of 4-Class** — A planet/not-planet classifier cannot distinguish eclipsing binaries from blends; ISRO judges specifically care about this discrimination. **Prevent by:** implementing the 4-class taxonomy from Day 1 (PC, EB, Blend, Other FP); validating that known EBs get > 70% probability in the EB class.

4. **Uncalibrated Confidence Scores** — Raw softmax probabilities are overconfident (0.94 may only be correct 72% of the time). Mission planners relying on these would waste follow-up resources on false positives. **Prevent by:** post-hoc temperature scaling on held-out validation set; reporting ECE and targeting < 0.04; labeling tiers as Gold (> 0.90), Silver (0.70–0.90), Bronze (< 0.70).

5. **MCMC Non-Convergence** — emcee chains that haven't mixed produce meaningless parameter uncertainties; "Period: 3.47 ± 0.001 days" when the true uncertainty is ± 0.5 days. **Prevent by:** initializing walkers from Nelder-Mead best-fit + Gaussian ball; checking acceptance fraction (0.2–0.5), autocorrelation time (τ ≤ N_steps / 50), and visual chain inspection; flagging non-converged runs; skipping MCMC entirely if Nelder-Mead χ²/ν > 3.

## Implications for Roadmap

Based on the dependency graph, architecture stages, feature priorities, and 30-hour hackathon constraint, a 4-phase roadmap is recommended. Phases 1–2 are sequential (hard dependencies), Phase 3 depends on Phase 2 outputs, and Phase 4 can overlap with Phase 3.

### Phase 1: Foundation — Data, Preprocessing & Detection (Stages 0–2)
**Rationale:** Everything depends on having clean, searchable light curves. This is the irreducible first step with the most downstream dependencies. Must complete within the first 8 hours of the hackathon. Pre-download Sector 1 data before the event to avoid MAST rate-limiting during the competition.

**Delivers:**
- ~60,000 preprocessed light curves (.npz per star)
- TLS periodograms for all targets
- First-pass candidate table (SDE ≥ 5, Parquet)
- Multi-planet iterative search results (3 iterations)
- BLS validation on top candidates

**Addresses features:** TESS data ingestion, preprocessing pipeline, TLS period search, multi-planet iterative search

**Avoids pitfalls:** Over-flattening (window_length ≥ 0.75 days), data gap interpolation (mask, don't fill), MAST rate-limiting (pre-download Sector 1), GPU memory overflow (batch 1000 LCs at a time)

**Research flag:** Standard patterns. lightkurve, TLS, wotan are well-documented with official NASA tutorials. Skip `/gsd-plan-phase --research-phase`.

### Phase 2: Intelligence — Feature Engineering & ML Training (Stages 3–4)
**Rationale:** Builds on Phase 1 detection results. CNN and XGBoost training can proceed in parallel (different input data, independent models). This is the most computationally intensive phase. Pre-trained Kepler weights must be available at Hour 0. Fine-tuning on TESS should complete within 2 hours on T4. Synthetic transit injection runs alongside training to augment the shallow-transit regime.

**Delivers:**
- Feature table (8+ engineered features per SDE ≥ 5 candidate, Parquet)
- Phase-folded light curve arrays (global 201-pt + local 61-pt views, .npz)
- Trained Dual-View CNN (Kepler pre-trained → TESS fine-tuned)
- Trained XGBoost model (stratified k-fold, F1-macro optimized)
- 4-class ensemble classifier with weighted softmax averaging
- Temperature-scaled confidence scores (Gold/Silver/Bronze tiers, ECE < 0.04)
- SHAP feature importance summary plot
- MLflow experiment tracking logs
- 7× augmented training dataset (synthetic transit injection inclusive)

**Addresses features:** Feature extraction, CNN training, XGBoost training, ensemble classification, confidence calibration, synthetic transit injection, 7× data augmentation, SHAP explainability, MLflow logging

**Avoids pitfalls:** Uncalibrated confidence (temperature scaling + ECE reporting), binary classification (4-class from Day 1), class imbalance (stratified k-fold + scale_pos_weight), GPU memory overflow on T4 (batch size 32, mixed precision), SHAP on CNN (run SHAP only on XGBoost via TreeExplainer), not pre-training (Kepler weights loaded at Hour 0)

**Research flag:** High-complexity ML phase. CNN architecture tuning, augmentation pipeline design, Kepler pre-training strategy, and ensemble weighting calibration all benefit from deep research. **Recommend `/gsd-plan-phase --research-phase 2`.**

### Phase 3: Characterization — Parameter Estimation & Validation (Stages 5–6)
**Rationale:** Runs exclusively on classified candidates from Phase 2. The two-gate design prevents wasted compute: only SDE ≥ 7 + confidence ≥ 0.70 candidates get Nelder-Mead; only confidence ≥ 0.85 (top ~15) get full MCMC. TRICERATOPS+ and SHERLOCK run only on top 5 Gold candidates. This phase can partially overlap with Phase 4 (visualization generation).

**Delivers:**
- Nelder-Mead batman transit fits for ~50 promising candidates
- MCMC posterior distributions for top 15 Gold candidates (median ± 1σ)
- Corner plots for converged MCMC chains
- TRICERATOPS+ FPP/NFPP for top 5 Gold planet candidates
- SHERLOCK benchmark comparison on top 5
- Centroid shift analysis from TPF data (top 200 by SDE)
- 4-panel diagnostic plots per SDE ≥ 7 candidate (PNG + Plotly HTML)
- Confusion matrix + classification metrics report
- Validation confirmation on WASP-121b, TOI-270, L 98-59

**Addresses features:** Parameter estimation (batman + MCMC), TRICERATOPS+ FPP, SHERLOCK benchmark, centroid analysis, 4-panel diagnostics, corner plots, confusion matrix, validation on known targets

**Avoids pitfalls:** MCMC non-convergence (Nelder-Mead initialization, convergence diagnostics, skip if χ²/ν > 3), hard-coded limb darkening (per-star quadratic from TICv8), TPF download timeout (async HTTP, timeout=30s, pre-filter to top 200), single-pass search (already handled in Phase 1 iterative search)

**Research flag:** TRICERATOPS+ integration (Gaia dependencies, contrast curves) and MCMC convergence criteria for emcee need research. **Recommend `/gsd-plan-phase --research-phase 3`.**

### Phase 4: Presentation — Dashboard & Report (Stage 7)
**Rationale:** Depends on all pipeline outputs being pre-rendered to `/outputs/`. Dashboard development can begin earlier with placeholder data, but final integration requires Phase 3 outputs. Report writing can overlap with Phase 3 since content is known from pipeline design. This phase must be presentation-ready by Hour 28 to allow 2 hours of dry-run practice before the final demo.

**Delivers:**
- Interactive Next.js dashboard with candidate table, per-star diagnostics modals, and celestial star map (RA/Dec via leaflet)
- Candidate catalogue CSV (TIC ID, period, depth, duration, SDE, class, disposition, confidence tier, parameter uncertainties)
- 4-page PDF report (Methods, Detection+Classification Results, Validation Rigor, Parameter Uncertainty)
- Completeness map (synthetic transit injection recovery fraction vs. depth/period)
- Final SHAP summary plot embedded in report

**Addresses features:** Interactive dashboard, candidate catalogue CSV, PDF report, completeness map

**Avoids pitfalls:** Dashboard build failure from large /outputs/ (> 500MB — compress PNGs to dpi=100, use WebP, lazy-load), PDF exceeding 4-page limit (embed only 2–3 best examples, reference rest by filename), Next.js leaflet star map projection (RA/Dec coordinate transform needs validation)

**Research flag:** Next.js leaflet star map (RA/Dec → screen coordinates), Plotly HTML embedding in Next.js iframes. Moderate complexity. **Optional `/gsd-plan-phase --research-phase 4`** if time permits; standard Next.js patterns otherwise.

### Phase Ordering Rationale

- **Phase 1 before Phase 2** — Hard dependency: ML training requires TLS periods, features require TLS outputs, phase-folding requires periods. No ML without detection.
- **Phase 2 before Phase 3** — Hard dependency: Parameter estimation requires classification outputs (confidence gates). You can't gate on confidence > 0.85 without the classifier.
- **Phase 3 and Phase 4 can overlap** — Phase 4 dashboard development can use placeholder data while Phase 3 generates final outputs. Report can be drafted in parallel with MCMC runs. This overlap is critical for fitting within 30 hours.
- **Pre-training is pre-hackathon** — Kepler CNN pre-training (34k TCEs, ~3–4 hours on T4) must complete before Hour 0. This is not a phase — it's a prerequisite.
- **The gating pattern minimizes compute risk** — Every expensive operation (MCMC, centroid analysis, TRICERATOPS+, SHERLOCK) runs on a filtered subset (top 15, top 200, top 5). This means later phases degrade gracefully if time runs short — the pipeline still produces results, just with fewer deep-characterized candidates.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 2 (ML Training):** CNN architecture specifics (Dual-View layer configuration), augmentation pipeline design, Kepler pre-training data format conversion, ensemble weighting calibration, temperature scaling implementation. Multi-source research required.
- **Phase 3 (MCMC + FPP):** TRICERATOPS+ installation and Gaia dependency chain, emcee convergence diagnostic thresholds for transit data, batman limb darkening interpolation from TICv8. Niche domain with sparse documentation.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation):** lightkurve, TLS, wotan, and astroquery are extensively documented by NASA and the astronomy community. Official tutorials exist. Well-trodden path.
- **Phase 4 (Presentation):** Next.js static export, shadcn/ui components, and fpdf2 report generation are standard web development patterns. Only the leaflet star map projection needs a spike.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries are community-standard, peer-reviewed (Hippke & Heller 2019, Shallue & Vanderburg 2018, Foreman-Mackey 2013), with comprehensive official documentation. Stack decisions backed by ADRs 0001–0019 in PROJECT.md. |
| Features | HIGH | Derived from ISRO BAH problem statement requirements, evaluation criteria, competitor analysis (SHERLOCK, ExoMiner++, AstroNet), and hackathon constraints. Feature priorities map directly to judge scoring categories. |
| Architecture | HIGH | 7-stage batch pipeline follows established patterns from SHERLOCK (6-module), ExoMiner++ (multi-branch ensemble), and AstroNet (Dual-View CNN). Component boundaries and data flow are clearly specified and matched to hackathon compute constraints. |
| Pitfalls | MEDIUM | Well-researched from literature (SHERLOCK's 98% TOI recovery analysis, ExoMiner++ training requirements) and community experience. However, MCMC convergence behavior on specific transit datasets and TRICERATOPS+ integration with Gaia contrast curves need runtime validation during the hackathon. |

**Overall confidence: HIGH**

The research is comprehensive and well-sourced. The primary uncertainty lies in runtime behavior of specific integrations (TRICERATOPS+, MCMC on low-SNR candidates) that can only be validated during execution. The gating design provides graceful degradation paths for all high-risk operations.

### Gaps to Address

- **MAST data availability during hackathon:** Multiple teams downloading simultaneously may cause rate-limiting. Mitigation: pre-download Sector 1 data before the event; have Sectors 2–3 queued as backup.
- **TRICERATOPS+ installation complexity:** Requires Gaia stellar parameters, contrast curves, and population priors not included in lightweight install. Mitigation: spike this dependency in Phase 3 planning; have a fallback to manual FPP estimation if installation fails.
- **Next.js leaflet star map projection:** RA/Dec celestial coordinates to screen coordinates is non-trivial for all-sky rendering. Mitigation: spike this during Phase 4 planning; Astropy can pre-compute projections if leaflet proves difficult.
- **Synthetic transit injection at extreme depths:** Recovery at 50 ppm (Earth-analog around Sun-like star) depends on photometric noise floor (CDPP). May not be detectable in a single sector. Mitigation: report completeness as a function of depth and period; acknowledge detection limits honestly.
- **GPU memory on Colab T4:** 7× data augmentation (85k samples × 201 points) may exceed T4 16GB VRAM. Mitigation: use batch size 32, mixed-precision training, and progressive loading. Have a fallback to 3× augmentation if memory is tight.
- **Ensemble disagreement cases:** When CNN and XGBoost softmax probabilities diverge by > 0.3, which model to trust? Mitigation: flag as "ENSEMBLE DISAGREEMENT" in catalogue; default to CNN for shape-driven cases (deep transits), XGBoost for feature-driven cases (blends). Document the heuristic.

## Sources

### Primary (HIGH confidence — peer-reviewed, official documentation)
- **lightkurve** — https://docs.lightkurve.org — NASA official TESS/Kepler Python library; data access, manipulation, BLS
- **AstroNet** — Shallue & Vanderburg (2018), AJ 155, 94 — Dual-View 1D CNN architecture for exoplanet classification
- **TLS** — Hippke & Heller (2019), A&A 623, A39 — Transit Least Squares algorithm; 10–15% improvement over BLS
- **batman** — Mandel & Agol (2002), ApJ 580, L171 — Analytic transit light curve model
- **emcee** — Foreman-Mackey et al. (2013) — MCMC ensemble sampler; astronomy community standard
- **ExoMiner++** — Valizadegan et al. (2025), AJ 170.5 — Multi-branch CNN + ensemble for TESS classification
- **SHERLOCK** — Dévora-Pajares et al. (2024), MNRAS 532, 4752 — 6-module end-to-end exoplanet vetting pipeline; 98% TOI recovery
- **TRICERATOPS+** — Gomez Barrientos et al. (2025), AJ 170:148 — Bayesian FPP/NFPP for TESS candidates
- **wotan** — https://github.com/hippke/wotan — State-of-the-art light curve detrending library
- **celerite2** — https://celerite2.readthedocs.io — Gaussian Process red noise modeling (Matérn-3/2 kernel)
- **Project ADRs** — ADR-0001 through ADR-0019 in PROJECT.md — Architecture decisions backing stack and design choices

### Secondary (MEDIUM confidence — community consensus, multiple sources agree)
- **ISRO BAH 2026 Problem Statement** — https://hack2skill.com/event/bah2026/ — Evaluation criteria, timeline, problem taxonomy
- **TESS Data Release Notes** — https://archive.stsci.edu/tess/ — Sector coverage, quality flags, known systematics
- **ExoFOP-TESS** — https://exofop.ipac.caltech.edu/tess/ — TOI labels used as training ground truth
- **Kepler DR24** — https://exoplanetarchive.ipac.caltech.edu/ — 34,032 TCEs for CNN pre-training

### Tertiary (LOW confidence — single source or inference, needs validation)
- **Next.js leaflet star map integration** — No known prior art for celestial coordinate rendering with react-leaflet; needs spike
- **TRICERATOPS+ Gaia dependency compatibility** — Version compatibility between TRICERATOPS+ (2025) and current Gaia DR3 archives; needs verification
- **Colab T4 GPU memory limits with 7× augmentation** — Theoretical estimate; actual memory usage depends on batch size and precision settings

---
*Research completed: 25 Jun 2026*
*Ready for roadmap: yes*
