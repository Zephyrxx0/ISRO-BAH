# Feature Research: Exoplanet Detection Pipeline

**Domain:** AI-enabled exoplanet detection from TESS photometry (ISRO BAH 2026 PS-07)
**Researched:** 25 Jun 2026
**Confidence:** HIGH
**Context:** 30-hour hackathon grand finale, judged by ISRO scientists, team of 3–4 students. Evaluation criteria: detection accuracy, classification accuracy, parameter estimation precision, confidence/uncertainty reporting.

## Feature Landscape

### Table Stakes (Must Ship — Missing Any = Incomplete Submission)

These are the features the problem statement **explicitly requires** and that ISRO judges will look for. They form the minimum viable pipeline.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **TESS data ingestion from MAST** | Problem statement mandates TESS 2-min cadence photometry. Without data, nothing else works. | LOW | `lightkurve` + `astroquery` handle this. ~2 hours for 3 sectors (~60k targets). Known pattern. |
| **Light curve preprocessing pipeline** | Raw TESS data contains NaNs, outliers, quality-flagged cadences, and stellar variability. Must detrend before transit search. | MEDIUM | Two-tier detrending: biweight (Wotan) for bulk LCs + Gaussian Process (celerite2) for top 100. Quality masking via TESS flags. Normalization. Exclude Tmag < 6 stars (saturation) and LCs with < 500 valid cadences. Mask (don't interpolate) 13-day data gaps. |
| **Transit period search with BLS/TLS** | Core detection algorithm. Must find periodic transit-like dips in 60k light curves. Outputs period, epoch, duration, depth, SDE, SNR. | HIGH | TLS recommended primary (10–15% more small-planet detections). BLS as validation on top candidates. GPU-accelerated via CuPy wrapper. Search 0.5–30 day periods at 50k frequency steps. SDE > 7 threshold for candidates. |
| **4-class classifier (PC, EB, Blend, Other FP)** | Problem statement requires multi-class classification. Binary (planet/not-planet) fails to address EB and blend false positives that ISRO scientists specifically care about. | HIGH | Ensembles CNN (deep learning on phase-folded LCs) + XGBoost (on engineered features). 4-class softmax output. Matches problem statement taxonomy. |
| **Engineered feature extraction (8+ features)** | Powers the XGBoost stage and individual vetting tests. ISRO judges understand these physical discriminators. | MEDIUM | odd/even depth difference, secondary eclipse depth, centroid shift, V-shape metric, CROWDSAP, duration/period ratio, SDE, SNR. Add chi² improvement and period coherence for bonus rigor. |
| **Parameter estimation (P, T₁₄, δ)** | Evaluation criteria explicitly rewards parameter accuracy. Without orbital parameters, the detection is incomplete. | HIGH | batman Mandel-Agol transit model fit per top candidate. Two-gate: Nelder-Mead quick fit (SDE > 7 + confidence > 0.70) → MCMC (confidence > 0.85). Report period, transit duration, depth with uncertainties. |
| **Confidence scores with calibration** | Problem requires "calibrated confidence/SNR scores so mission planners can triage candidates reliably." | MEDIUM | Temperature-scaled softmax probabilities from ensemble. Target ECE < 0.04. Gold (> 0.90), Silver (0.70–0.90), Bronze (< 0.70) tiers. Judges understand calibration from peer-reviewed literature. |
| **Phase-folded visualization (minimum: raw LC + periodogram + phase-fold + classifier)** | Problem requires visualization of detections. Judges must see the transit signal is real. | MEDIUM | 4-panel diagnostic per SDE ≥ 7 candidate: (1) raw+detrended LC, (2) TLS periodogram, (3) phase-folded LC + batman model, (4) classifier softmax bar chart. PNG output. |
| **Candidate catalogue CSV output** | Required deliverable. Maps to what mission scientists actually use. | LOW | TIC ID, period, depth, duration, SDE, classification label, disposition, confidence tier, parameter uncertainties. One row per candidate. |
| **Validation on known targets (WASP-121b, TOI-270, L 98-59)** | Required to demonstrate pipeline works. Papers use such benchmarking. ISRO judges will ask "did it find the known planets?" | LOW | WASP-121b (hot Jupiter, easy sanity check). TOI-270 (3-planet system, multi-planet validation). L 98-59 (3 small planets). TOI-700 d as bonus. Period within 1%, depth within 10%. |
| **Confusion matrix + classification metrics** | Quantitative evaluation rigor. Judges expect precision/recall/F1 per class, ROC-AUC, confusion matrix heatmap. | LOW | sklearn classification_report + confusion matrix. Target > 90% accuracy on ExoFOP-labelled test set. |
| **4-page PDF report** | Required deliverable. Maps to 4 evaluation criteria: Methods, Detection+Classification Results, Validation Rigor, Parameter Uncertainty. | LOW | fpdf2 generation. Include pipeline diagram, result tables, key plots, assumptions declared. |
| **End-to-end single-command execution** | Hackathon deliverable must be runnable. Judges may ask to re-run on a test star. | LOW | Shell script wrapping the Python pipeline entry point. Ingest TESS FITS → output classified CSV. |

### Differentiators (Win the Hackathon — Separate from Average Submissions)

These features go beyond the problem statement minimum. Most teams will do bare-minimum detection + binary classification. These features signal sophistication, cite peer-reviewed literature, and demonstrate the "bonus points" that win prizes.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **TLS over BLS as primary** | Detects 10–15% more planets, especially small ones. Judges know BLS is the old standard and TLS is the modern improvement (Hippke & Heller 2019). States "we used the state-of-the-art." | LOW | `transitleastsquares` package is drop-in. Already in the pipeline by design. |
| **CNN + XGBoost ensemble (not single model)** | Combines deep learning shape recognition with physics-based feature discriminators. Follows ExoMiner++ pattern. Higher accuracy than either alone. | MEDIUM | Weighted average (0.6 × CNN + 0.4 × XGBoost). Must train both models, but ensemble inference is trivial. |
| **Kepler pre-training + TESS fine-tuning** | Demonstrates transfer learning sophistication. Kepler DR24 provides 34k labeled TCEs, far more than TESS alone. Shows knowledge of the literature (AstroNet, ExoMiner++). | MEDIUM | Pre-train CNN on Kepler data before hackathon. Fine-tune on TESS ExoFOP TOI labels during hackathon. Saves training time. |
| **MCMC parameter estimation (batman + emcee)** | Goes beyond point estimates. Full Bayesian posterior with 68% credible intervals. Corner plots are publication-quality and visually impressive. | HIGH | Only on top 15 Gold candidates (avoids blowing compute budget). Requires careful convergence checks (acceptance fraction 0.2–0.5). Two-gate design prevents wasted MCMC on false positives. |
| **Temperature-scaled confidence + ECE reporting** | Most teams report raw softmax. Calibrated confidence ("94% means correct 94% of the time") is what mission planners need. ECE < 0.04 is a specific, citable target. | MEDIUM | Post-hoc temperature scaling on held-out validation set. Single scalar parameter. |
| **Centroid shift analysis from TPF data** | Background blends are the hardest false positive class. Centroid analysis proves you're not just classifying on light curve shape — you're doing pixel-level vetting. | MEDIUM | Requires downloading TPFs via TESScut. Compute flux-weighted centroid during transit vs. out-of-transit. Shift > 3σ → blend. Adds ~2 hours to pipeline. |
| **Synthetic transit injection + completeness map** | Direct evidence of pipeline sensitivity. Shows what depths/periods you can and cannot detect. Visually impressive: judges see the detection boundary moving as SNR changes. | HIGH | Generate batman-model transits at known depths (50–2000 ppm), inject into real TESS noise, measure recovery fraction. ~3.5 hours on T4 GPU for 7× augmented training set. |
| **Multi-planet iterative search and removal** | TOI-270 and L 98-59 are multi-planet systems. Iterative search demonstrates you didn't stop at the first signal. Professional pipelines do this. | MEDIUM | After finding signal 1, mask its transits and re-run TLS. Implement at least 3 iterations. |
| **SHAP feature importance explainability** | XAI (explainable AI) is a major differentiator. Shows judges *why* the model made a decision. "The classifier flagged this as an EB because odd/even depth differed by 4.2σ." | LOW | SHAP TreeExplainer on XGBoost. One summary plot. No additional training needed. |
| **TRICERATOPS+ FPP/NFPP validation** | Community-standard Bayesian false positive probability. FPP < 1.5% + NFPP < 0.1% = "Validated Planet." This is the same language used in professional exoplanet discovery papers. | MEDIUM | Run on top 5 Gold planet candidates only. Requires Gaia stellar parameters and contrast curves. Imports heavyweight dependency but only for final validation gate. |
| **SHERLOCK benchmark comparison** | Cite that your pipeline matches SHERLOCK (which recovers 98% of TOIs) on overlapping candidates. Third-party credibility. | LOW | Run SHERLOCK on top 5 as independent check. Cite Dévora-Pajares et al. (2024). |
| **Interactive Next.js dashboard** | Most teams submit CSV + static PNGs. An interactive dashboard where judges can click stars, view light curves, and toggle confidence tiers is memorable. | HIGH | Pre-render all visuals in Python pipeline. Next.js reads from /outputs/ directory. No live Python backend needed. Celestial star map (RA/Dec via Astropy + folium/leaflet). ~5 hours of work. |
| **MLflow experiment tracking** | Reproducibility is a major scoring point. Shows professional ML engineering practices. | LOW | Log hyperparameters, metrics, model artifacts. Auto-logging via mlflow.tensorflow.autolog(). Trivial setup, big signalling value. |
| **Data augmentation (7×) + stratified sampling** | Addresses shallow-transit underrepresentation in real labels. Demonstrates understanding of class imbalance and data scarcity problems in astronomy ML. | MEDIUM | Noise injection, transit time jitter, flux scaling, phase-folding jitter. Synthetic transit injection for shallow depths. Stratified k-fold (k=5). |

### Anti-Features (Deliberately NOT Build at a 30-Hour Hackathon)

These features seem attractive but are scope-killers. They either take too long, add complexity without scoring points, or are explicitly out of scope per the problem constraints.

| Feature | Why Avoid | What to Do Instead |
|---------|-----------|-------------------|
| **Real-time streaming data processing** | TESS data is batch archive access. Building streaming infrastructure (Kafka, WebSockets) wastes 8+ hours. Not in evaluation criteria. | Offline batch pipeline. Single-command execution: `python run_pipeline.py --sectors 1,2,3`. |
| **Full atmospheric characterization (transit spectroscopy)** | Requires transmission spectroscopy analysis of planetary atmospheres (H₂O, CO₂, CH₄ detection). Completely different problem domain. Weeks of work. Not in problem statement. | Mention as "future work with JWST/Roman" in report limitations section. |
| **Training large transformer from scratch** | Bi-LSTM + Transformer architecture proposed in submission doc would need > 4 hours training on T4 GPU. Risk of not finishing. AstroNet-style CNN is peer-reviewed and faster. | Use Dual-View CNN (AstroNet architecture, ~2.5M parameters). Pre-train on Kepler before hackathon. Fine-tune on TESS during hackathon (< 2 hours). |
| **OAuth / user authentication for dashboard** | Read-only static viewer is sufficient. Auth adds security complexity (JWT, sessions, CSRF) that no judge will test and that takes 3+ hours to implement correctly. | Next.js read-only dashboard. No login. Pre-rendered visuals from /outputs/. |
| **Custom data format (HDF5 while project decided .npz + Parquet)** | HDF5 adds dependency complexity. .npz + Parquet is zero-dependency beyond NumPy, isolates per-star corruption, enables columnar querying. ADR-0009 already decided. | `.npz` per light curve + Parquet master catalogue. |
| **Live Python backend for dashboard** | Adding Flask/FastAPI requires process management, CORS, error handling, and deployment. Next.js reading pre-rendered files eliminates all of this. | Pre-render all visuals in pipeline. Next.js static site from /outputs/. No server-side Python at runtime. |
| **Binary classification only** | Problem statement explicitly requires multi-class. "Planet / not-planet" discards the EB and blend discrimination that ISRO evaluators care about. | 4-class taxonomy: PLANET CANDIDATE, ECLIPSING BINARY, BACKGROUND BLEND, STELLAR VARIABILITY. |
| **Treating instrumentals as a classifier class** | Instrumental artefacts (momentum dumps, scattered light) are non-astrophysical and handled by TESS quality flags. Adding them as a 5th class dilutes training data and confuses the model. | Preprocessing gate: remove quality-flagged cadences. Classifier sees only astrophysical signals (4 classes). ADR-0006 already decided. |
| **Interpolating over 13-day TESS data gaps** | Interpolation over 13-day gaps creates synthetic structure that TLS may falsely detect as a signal. Masking is the correct approach. | Mask data gaps. TLS handles masked arrays natively. ADR-0013 already decided. |
| **Using VESPA for FPP** | VESPA has been retired and unmaintained since 2023. Community standard is now TRICERATOPS+. Using VESPA signals outdated knowledge. | TRICERATOPS+ (Gomez Barrientos et al. 2025). FPP < 1.5%, NFPP < 0.1%. |
| **Hard-coded limb darkening coefficients** | Systematic depth error from fixed coefficients. Per-star interpolation from TICv8 using Claret & Bloemen (2011) tables is essentially free (only 15 MCMC runs). | Per-star quadratic limb darkening from TICv8. |
| **Multi-sector search beyond 3 sectors** | 3 sectors (Sectors 1, 2, 3) already extends detectable period range to ~81 days and is sufficient for cross-sector validation. Adding more sectors blows up data download and processing time. | Pitch scalability to all 26 sectors. Only process 3 for the hackathon. |

## Feature Dependencies

```
TESS Data Ingestion
    └──requires──> MAST API access (lightkurve/astroquery)

Light Curve Preprocessing
    └──requires──> TESS Data Ingestion

Transit Period Search (TLS)
    └──requires──> Preprocessed (detrended) light curves

Feature Extraction (8+ engineered features)
    └──requires──> TLS results (period, epoch, duration, depth)
    └──enhances──> Centroid Analysis (needs TPF data separately downloaded)

Phase Folding (CNN inputs)
    └──requires──> TLS period + epoch
    └──requires──> Preprocessed light curve

CNN Training
    └──requires──> Phase-folded light curves (global + local views)
    └──enhances──> Kepler pre-training (separate, pre-hackathon)
    └──enhances──> Data augmentation (synthetic transit injection)

XGBoost Training
    └──requires──> Feature extraction (engineered features)
    └──enhances──> SHAP explainability (requires trained XGBoost)

Ensemble Classification
    └──requires──> Trained CNN model
    └──requires──> Trained XGBoost model
    └──requires──> Both sets of input data (phase-folded LCs + features)

Confidence Calibration (Temperature Scaling)
    └──requires──> Ensemble softmax outputs on validation set

Parameter Estimation (batman + MCMC)
    └──requires──> TLS period + epoch (initialization)
    └──requires──> Classification confidence > 0.70 (gate)
    └──enhances──> MCMC (requires batman Nelder-Mead fit; confidence > 0.85 gate)

TRICERATOPS+ FPP
    └──requires──> Classification output (planet candidates)
    └──requires──> Gaia stellar parameters + contrast curves

4-Panel Diagnostic Visualization
    └──requires──> TLS results
    └──requires──> Classification output
    └──enhances──> MCMC corner plots (requires MCMC results)

Interactive Dashboard (Next.js)
    └──requires──> Pre-rendered PNGs + candidate catalogue CSV
    └──requires──> All pipeline outputs written to /outputs/

PDF Report
    └──requires──> All analysis complete
    └──requires──> Candidate catalogue finalized

Synthetic Transit Injection + Completeness Map
    └──requires──> batman transit model
    └──requires──> Real detrended TESS noise samples (inject targets into)
    └──enhances──> Data augmentation (provides shallow-transit training samples)
```

### Dependency Notes

- **Ensemble requires both CNN and XGBoost trained:** Both paths can be developed in parallel (ML lead + Data lead). Independent until final weighted average.
- **Parameter estimation requires classification gate:** Don't run expensive MCMC on false positives. Two-gate design (SDE > 7 + confidence > 0.70 → Nelder-Mead; confidence > 0.85 → MCMC) saves ~5 hours of compute.
- **Centroid analysis is independent of other feature extraction:** Requires separate TPF download via TESScut. Can be parallelized.
- **SHAP is independent of other pipeline stages:** Can run after XGBoost is trained. No downstream dependency.
- **Interactive dashboard depends on all pipeline outputs being pre-rendered:** Must be done after pipeline completes. Can be developed in parallel with report writing using placeholder data.

## MVP Definition

### Launch With (v1 — Minimum Hackathon Submission)

**Pipeline core — must complete in first 20 hours:**
- [ ] TESS data ingestion (3 sectors, ~60k targets) — **no pipeline without data**
- [ ] Preprocessing pipeline (biweight detrending, quality masking, normalization) — **fundamental prerequisite**
- [ ] TLS period search on all targets with SDE ≥ 5 loose filter — **core detection**
- [ ] Feature extraction (8+ features) per candidate — **powers XGBoost + vetting**
- [ ] Phase-folding (global + local views) — **CNN inputs**
- [ ] CNN training (Kepler pre-trained + TESS fine-tuned) — **deep learning classifier**
- [ ] XGBoost training on engineered features — **feature-based classifier**
- [ ] Ensemble classification with 4-class output — **required by problem**
- [ ] Temperature-scaled confidence scores (Gold/Silver/Bronze tiers) — **required by problem**
- [ ] Parameter estimation (batman Nelder-Mead) on top 15 planet candidates — **required by problem**
- [ ] Candidate catalogue CSV — **required deliverable**

**Visualization + validation — can overlap with pipeline runs (hours 16–24):**
- [ ] 4-panel diagnostic plots per SDE ≥ 7 candidate — **required visualization**
- [ ] Confusion matrix + classification metrics — **quantitative rigor**
- [ ] Validation on WASP-121b, TOI-270, L 98-59 — **proves pipeline works**
- [ ] 4-page PDF report — **required deliverable**

### Add After Core Works (v1.x — Differentiator Layer, hours 20–28)

**Features to add once pipeline runs end-to-end and generates a candidate catalogue:**

- [ ] MCMC parameter estimation on top 5 Gold candidates — **trigger: batman Nelder-Mead fit succeeds**
- [ ] SHAP feature importance summary plot — **trigger: XGBoost training complete**
- [ ] Multi-planet iterative search (3 iterations) on all targets — **trigger: TLS first-pass complete**
- [ ] Synthetic transit injection + completeness map — **trigger: augmentation pipeline functional**
- [ ] TRICERATOPS+ FPP on top 5 Gold candidates — **trigger: classification complete**
- [ ] SHERLOCK benchmark comparison on top 5 — **trigger: top candidates identified**
- [ ] MLflow logging activated — **trigger: any training run**

### If Everything Goes Well (v2 — Competition-Winning Layer, hours 24–30)

- [ ] Interactive Next.js dashboard (candidate table, per-star diagnostics, star map) — **trigger: all visuals pre-rendered**
- [ ] Centroid shift analysis from TPF data — **trigger: TPF download complete (prerequisite for blend classification rigor)**
- [ ] Corner plots for MCMC posterior distributions — **trigger: MCMC chains converged**

### Future Consideration (Post-Hackathon)

- [ ] Scale to all 26 TESS sectors — **pipeline designed for 3; scalable claim for pitch**
- [ ] Full atmospheric characterization — **completely different domain (spectroscopy)**
- [ ] Extension to Roman Space Telescope data — **2026+ data format, pitch-only**
- [ ] Real-time alert system for new TESS sectors — **streaming infrastructure not in scope**
- [ ] Automated paper-writing (LaTeX generation from results) — **nice but not hackathon-relevant**

## Feature Prioritization Matrix

| Feature | User Value (Judge Impact) | Implementation Cost (Hours) | Priority |
|---------|---------------------------|----------------------------|----------|
| TESS Data Ingestion | CRITICAL | 3h | P0 |
| Preprocessing Pipeline | CRITICAL | 3h | P0 |
| TLS Period Search | CRITICAL | 4h | P0 |
| Feature Extraction | HIGH | 2h | P1 |
| 4-Class CNN Training | CRITICAL | 4h (pre-trained) | P0 |
| XGBoost Training | HIGH | 1h | P1 |
| Ensemble Classification | CRITICAL | 1h | P0 |
| Confidence Calibration | HIGH | 1h | P1 |
| Parameter Estimation (batman) | CRITICAL | 3h | P0 |
| MCMC (emcee) | HIGH | 3h | P1 |
| Candidate Catalogue CSV | CRITICAL | 1h | P0 |
| 4-Panel Diagnostics | HIGH | 2h | P1 |
| Confusion Matrix + Metrics | MEDIUM | 1h | P2 |
| Validation on Known Targets | CRITICAL | 2h | P0 |
| PDF Report | CRITICAL | 3h | P0 |
| SHAP Explainability | HIGH | 1h | P1 |
| Multi-Planet Iterative Search | MEDIUM | 2h | P1 |
| Synthetic Transit Injection | HIGH | 3h | P1 |
| TRICERATOPS+ FPP | HIGH | 2h | P2 |
| Centroid Analysis | HIGH | 2h | P2 |
| Interactive Dashboard | HIGH | 5h | P2 |
| MLflow Logging | MEDIUM | 0.5h | P1 |
| SHERLOCK Comparison | MEDIUM | 1h | P2 |
| Data Augmentation (7×) | HIGH | 3h | P1 |

**Priority key:**
- P0: Must have to submit. Blocking. Non-negotiable.
- P1: Strongly recommended. Significant impact-to-cost ratio. Ship if possible.
- P2: Differentiator. Ship only if core (P0+P1) is stable. These win competitions.

## Competitor Feature Analysis

| Feature | SHERLOCK (Dévora-Pajares 2024) | ExoMiner++ (NASA, Valizadegan 2025) | AstroNet (Google, Shallue 2018) | Our Approach |
|---------|-------------------------------|--------------------------------------|--------------------------------|--------------|
| Detection algorithm | BLS | SPOC TCE input (no own detection) | None (classifies pre-detected TCEs) | TLS (primary) + BLS (validation) |
| Classification | 4-class vetting | 2-class (PC vs FP) for 2-min | 2-class (PC vs FP) | 4-class (PC, EB, Blend, Other FP) |
| ML Architecture | Rule-based + statistical tests | Multi-branch CNN (periodogram, flux trend, diff image, unfolded flux, attitude) | Dual-View 1D CNN | Dual-View CNN + XGBoost ensemble |
| Parameter Estimation | Bayesian MCMC (emcee) | Not included (separate tool) | Not included | batman + emcee (inline, two-gate) |
| FPP Calculation | Own statistical validation | Not included | Not included | TRICERATOPS+ (community standard) |
| Training data source | Kepler + TESS | Kepler + TESS (transfer learning) | Kepler only | Kepler pre-training + TESS fine-tuning |
| Data augmentation | — | — | — | 7× (noise, jitter, rescaling, synthetic injection) |
| Explainability | — | Integrated XAI | — | SHAP on XGBoost |
| Compute requirements | — | Multi-GPU (V100/A100) | — | Single T4 GPU (Colab free tier) |
| Interactive output | — | Dash web app catalog | — | Next.js dashboard (pre-rendered) |
| Completeness map | — | — | — | Synthetic transit injection |
| Confidence calibration | — | — | — | Temperature scaling + ECE < 0.04 |

**Key differentiators from competitors:**
- **4-class classification** is broader than AstroNet (binary) and matches SHERLOCK's vetting scope while being ML-driven rather than rule-based.
- **Inline MCMC** means no separate post-processing tool needed — parameters come from the same pipeline.
- **TLS detection** gives us 10–15% more small planets than BLS-only pipelines.
- **Ensemble architecture** combines deep learning and feature-based classification — neither AstroNet nor ExoMiner++ does this.
- **Single T4 GPU compatibility** is a practical advantage. ExoMiner++ requires V100/A100 clusters.
- **Temperature-scaled confidence with ECE** is a calibration rigor that most competitors don't report.

## Sources

- **Project documents:** `main.md` (Sections 2–13, 20, 24), `CONTEXT.md` (domain glossary), `PROJECT.md` (key decisions)
- **Competitor: ExoMiner++** — NASA Ames, Valizadegan et al. (2025), AJ 170.5. GitHub: https://github.com/nasa/ExoMiner. Multi-branch CNN architecture. Identified 7,330 planet candidates from 147,568 unlabelled TCEs.
- **Competitor: SHERLOCK** — Dévora-Pajares et al. (2024), MNRAS 532, 4752. 6-module end-to-end pipeline. 98% TOI recovery rate.
- **Competitor: AstroNet** — Shallue & Vanderburg (2018), AJ 155, 94. Dual-View 1D CNN. Kepler DR24 classifier. GitHub: https://github.com/google-research/exoplanet-ml
- **TRICERATOPS+** — Gomez Barrientos et al. (2025), AJ 170:148. Bayesian FPP/NFPP for TESS candidates.
- **BAH 2026 Official Site** — https://hack2skill.com/event/bah2026/. Evaluation criteria, timeline, problem statements.
- **TLS Algorithm** — Hippke & Heller (2019), A&A 623, A39. Transit Least Squares paper.
- **batman** — Mandel & Agol (2002), ApJ 580, L171. Analytic transit model.
- **emcee** — Foreman-Mackey et al. (2013). MCMC ensemble sampler.

---

*Feature research for: ISRO BAH 2026 PS-07 — Exoplanet Detection Pipeline*
*Researched: 25 Jun 2026*
