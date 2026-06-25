# Architecture Patterns

**Domain:** AI-enabled exoplanet detection pipeline (TESS transit photometry)
**Researched:** 25 Jun 2026
**Confidence:** HIGH
**Sources:** main.md Section 4 (Full Pipeline Architecture), ExoMiner++ architecture, AstroNet paper, SHERLOCK pipeline design, project ADRs

## Recommended Architecture

### 7-Stage Batch Pipeline with Pre-Rendered Frontend

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        FULL PIPELINE ARCHITECTURE                         │
│                                                                          │
│  STAGE 0: DATA INGESTION                                                 │
│  ─────────────────────                                                   │
│  MAST API (lightkurve/astroquery)                                        │
│    ↓ async HTTP parallel download (4× speed)                             │
│  ~60,000 .npz light curve files + TIC stellar parameters (Parquet)       │
│                                                                          │
│  STAGE 1: PREPROCESSING                                                  │
│  ─────────────────────                                                   │
│  Quality mask → outlier clip (5σ) → normalize → biweight detrend         │
│    ↓ Tmag < 6 filter | valid cadences ≥ 500 | mask 13-day gaps           │
│  Cleaned flux arrays (.npz per star)                                     │
│                                                                          │
│  STAGE 2: PERIOD SEARCH                                                  │
│  ────────────────────                                                    │
│  TLS on all targets (0.5–30 day, 50k freq steps)                        │
│    ↓ SDE ≥ 5 loose filter → extract period, t₀, duration, depth, SNR    │
│  Multi-planet iterative search (3 iterations) on all targets             │
│    ↓ BLS validation on top candidates                                    │
│  Candidate table (Parquet): TIC ID + TLS outputs                         │
│                                                                          │
│  STAGE 3: FEATURE EXTRACTION                                             │
│  ─────────────────────────                                              │
│  For each SDE ≥ 5 candidate:                                             │
│    odd/even depth diff | secondary eclipse | centroid shift | V-shape    │
│    CROWDSAP | duration/period | depth ratio | chi² improvement            │
│    + TPF download (TESScut) for centroid analysis on top 500             │
│  Phase folding: 201-pt global view + 61-pt local view (CNN inputs)       │
│  Features table (Parquet) + phase-folded arrays (.npz)                   │
│                                                                          │
│  STAGE 4: ML CLASSIFICATION                                              │
│  ────────────────────────                                                │
│  ┌─────────────┐     ┌──────────────┐                                   │
│  │  CNN MODEL   │     │ XGBoost MODEL │                                  │
│  │  (TensorFlow)│     │  (sklearn)    │                                   │
│  │              │     │               │                                   │
│  │ Dual-View    │     │ 8+ features   │                                   │
│  │ 1D CNN       │     │ per candidate │                                   │
│  │ Global: 201  │     │               │                                   │
│  │ Local:  61   │     │               │                                   │
│  └──────┬───────┘     └───────┬───────┘                                   │
│         │                     │                                          │
│         └──────┬──────────────┘                                          │
│                ↓                                                         │
│         ┌─────────────┐                                                  │
│         │  ENSEMBLE    │  0.6 × CNN + 0.4 × XGBoost                      │
│         │  4-class     │  → PLANET CANDIDATE / ECLIPSING BINARY          │
│         │  softmax     │  → BACKGROUND BLEND / STELLAR VARIABILITY       │
│         └──────┬───────┘                                                  │
│                ↓                                                         │
│         ┌─────────────┐                                                  │
│         │ TEMPERATURE  │  Post-hoc calibration on held-out validation     │
│         │  SCALING     │  Target ECE < 0.04                               │
│         └──────┬───────┘  Gold (>0.90) / Silver (0.70-0.90) / Bronze     │
│                ↓                                                         │
│  Classification table (Parquet): TIC ID + 4 probabilities + tier         │
│                                                                          │
│  STAGE 5: PARAMETER ESTIMATION                                           │
│  ────────────────────────────                                            │
│  GATE 1: SDE ≥ 7 AND PC confidence ≥ 0.70                                │
│    → batman Nelder-Mead fit (fast analytic)                              │
│  GATE 2: PC confidence ≥ 0.85 (top 15)                                   │
│    → batman + emcee MCMC (32 walkers, 5000 steps)                        │
│    → Corner plots (corner)                                               │
│    → Report median ± 1σ (16th/84th percentile)                            │
│  TOP 5 GOLD (PC confidence > 0.90):                                      │
│    → TRICERATOPS+ FPP/NFPP validation                                    │
│    → SHERLOCK benchmark comparison                                       │
│  Parameter table (Parquet): P, T₁₄, δ, Rp/Rs, i, a/Rs with uncertainties │
│                                                                          │
│  STAGE 6: OUTPUT & VISUALIZATION                                         │
│  ──────────────────────────────                                          │
│  Per SDE ≥ 7 candidate: 4-panel diagnostic (PNG + Plotly HTML)           │
│  Panel 1: Raw + detrended LC | Panel 2: TLS periodogram                  │
│  Panel 3: Phase-folded + batman model | Panel 4: Classifier softmax bar   │
│  Per top 15 MCMC: corner plot (PNG)                                      │
│  Summary: confusion matrix heatmap, SHAP summary plot                     │
│  All written to /outputs/plots/ and /outputs/data/                        │
│                                                                          │
│  STAGE 7: REPORT & DASHBOARD                                             │
│  ──────────────────────────                                             │
│  Candidate catalogue CSV → /outputs/catalogue.csv                        │
│  4-page PDF report → /outputs/report.pdf                                 │
│  Next.js dashboard reads /outputs/ (pre-rendered, no Python backend)     │
│  Dashboard features: candidate table, per-star diagnostics, star map     │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Data Ingestor** | Download TESS 2-min cadence FITS files from MAST for 3 sectors (~60k targets). Store as .npz per star. Query TICv8 for stellar parameters. | Preprocessor (writes .npz files); TIC Catalogue (reads Parquet) |
| **Preprocessor** | Quality-mask, normalize, detrend (biweight), mask data gaps. Output cleaned flux arrays. Discard invalid LCs (Tmag < 6, < 500 cadences). | Data Ingestor (reads .npz); Period Searcher (writes cleaned .npz) |
| **Period Searcher** | Run TLS on all targets. Multi-planet iterative search. Compute SDE, SNR, period, t₀, duration, depth. BLS validation on top candidates. | Preprocessor (reads cleaned .npz); Feature Extractor (writes candidate table Parquet) |
| **Feature Extractor** | Compute 8+ engineered features per candidate. Phase-fold light curves. Download TPFs for centroid analysis on top 500. | Period Searcher (reads candidate table); ML Classifier (writes features + phase-folded arrays) |
| **CNN Trainer** | Dual-View 1D CNN. Kepler pre-trained weights loaded. Fine-tune on TESS ExoFOP TOI labels. 7× data augmentation. | Feature Extractor (reads phase-folded arrays); ML Classifier (writes model .h5) |
| **XGBoost Trainer** | Gradient boosted trees on engineered features. Stratified k-fold (k=5). F1-macro optimization. | Feature Extractor (reads features table); ML Classifier (writes model .json) |
| **Ensemble Classifier** | Weighted softmax average (0.6×CNN + 0.4×XGBoost). 4-class output. Temperature scaling for calibration. | CNN Trainer, XGBoost Trainer (reads models); Parameter Estimator (writes classification table) |
| **Parameter Estimator** | Two-gate: Nelder-Mead batman fit → MCMC emcee. TRICERATOPS+ FPP on top 5 Gold. | Ensemble Classifier (reads classifications); Output Generator (writes parameter table) |
| **Output Generator** | 4-panel diagnostics (PNG + Plotly HTML). Corner plots. Confusion matrix. SHAP summary. Candidate catalogue CSV. 4-page PDF report. | Parameter Estimator (reads parameters); Dashboard (writes to /outputs/) |
| **Next.js Dashboard** | Read-only static viewer. Candidate table with filters (confidence tier, class). Per-star diagnostics modal. Celestial star map (RA/Dec). | Output Generator (reads /outputs/ directory); No live backend |
| **MLflow Tracker** | Log hyperparameters, metrics, model artifacts. Version control for training runs. | CNN Trainer, XGBoost Trainer (logs during training) |

### Data Flow

```
MAST Archive (FITS)
    ↓ lightkurve + astroquery async download
.npz per star (raw flux + time + flux_err)
    ↓ preprocessing (quality mask, normalize, detrend)
.npz per star (cleaned flux)
    ↓ TLS period search + iterative multi-planet removal
Parquet candidate table (TIC ID, period, t₀, duration, depth, SDE, SNR)
    ↓ feature extraction + phase folding
Parquet features table + .npz phase-folded arrays (201-pt global, 61-pt local)
    ↓ CNN inference + XGBoost inference
Classification scores (4-class softmax)
    ↓ temperature scaling
Calibrated confidence tiers (Gold/Silver/Bronze)
    ↓ two-gate parameter estimation
Orbital parameters with uncertainties (median ± 1σ)
    ↓ pre-rendered outputs
/outputs/plots/*.png, /outputs/plots/*.html, /outputs/catalogue.csv, /outputs/report.pdf
    ↓ Next.js static site
Interactive dashboard
```

## Patterns to Follow

### Pattern 1: Two-Gate Parameter Estimation
**What:** Separate cheap analytic fit from expensive MCMC sampling. Gate 1 (SDE ≥ 7 + confidence ≥ 0.70) triggers fast batman Nelder-Mead. Gate 2 (confidence ≥ 0.85) triggers full MCMC on top 15 only.
**When:** Always when parameter estimation cost varies by 100× between methods. Prevents hours of MCMC on false positives.
**Why:** MCMC on 60k candidates would take days. Two-gate reduces MCMC runs to 15, fitting within the 30-hour window.
**Example:**
```python
# Gate 1: Quick fit for all promising candidates
if sde >= 7 and pc_confidence >= 0.70:
    params_nm = scipy.optimize.minimize(neg_log_likelihood, x0, method='Nelder-Mead')
    # Gate 2: Full MCMC only for highest confidence
    if pc_confidence >= 0.85:
        sampler = emcee.EnsembleSampler(nwalkers=32, ndim=5, log_prob_fn=...)
        sampler.run_mcmc(pos, 5000)
```

### Pattern 2: Pre-Rendered Static Frontend
**What:** Python pipeline pre-renders all visual outputs (PNG, HTML, JSON). Next.js reads from /outputs/ directory as a static site. No live Python server.
**When:** Hackathon with fixed compute budget, output-only visualization needs, and no real-time data.
**Why:** Eliminates server-side complexity (CORS, process management, deployment). Judges interact with what the pipeline already computed. Next.js builds in seconds.
**Example:**
```
Pipeline: write /outputs/plots/TIC_22529346_panel.html
Dashboard: <iframe src="/outputs/plots/TIC_22529346_panel.html" />
```

### Pattern 3: Ensemble with Weighted Softmax Averaging
**What:** Combine CNN (deep learning, phase-folded LCs) and XGBoost (shallow learning, engineered features) predictions via weighted average of softmax probabilities.
**When:** When two models learn complementary signal features (shape vs. physics metrics) and runtimes are compatible.
**Why:** CNN excels at transit morphology recognition but can't use physics priors (odd/even depth, centroid shift). XGBoost uses those priors but can't learn raw shape. Weighting 0.6×CNN + 0.4×XGBoost follows ExoMiner++ pattern and ADR-0001.
**Example:**
```python
p_cnn = cnn_model.predict(phase_folded_lc)     # shape: (4,)
p_xgb = xgb_model.predict_proba(features_df)    # shape: (4,)
final_proba = 0.6 * p_cnn + 0.4 * p_xgb
predicted_class = np.argmax(final_proba)
```

### Pattern 4: Pre-Training + Fine-Tuning Transfer Learning
**What:** Train CNN on Kepler DR24 (34k TCEs, well-labeled) before hackathon. Fine-tune on TESS ExoFOP TOIs during hackathon.
**When:** Target domain (TESS) has fewer labels than source domain (Kepler), and both share the same signal morphology (transit shapes are universal).
**Why:** Kepler has 34k labeled TCEs; TESS ExoFOP has ~5k. Pre-training gives a strong shape prior. Fine-tuning adapts to TESS-specific noise, cadence, and systematics in < 2 hours.
**Example:**
```python
# Pre-hackathon (not time-limited)
cnn = build_transit_cnn()
cnn.fit(kepler_phase_folded, kepler_labels, epochs=50)
cnn.save('kepler_pretrained.h5')

# During hackathon
cnn = load_model('kepler_pretrained.h5')
cnn.fit(tess_phase_folded, tess_labels, epochs=10, lr=1e-4)  # Fine-tune
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Over-Flattening During Detrending
**What:** Using too-short a window length in biweight or Savitzky-Golay detrending, which erases transit signals along with stellar variability.
**Why bad:** A transit of duration 3 hours can be indistinguishable from short-timescale stellar variability. If the detrending window is shorter than ~3× transit duration, the transit signal is partially or fully removed.
**Instead:** Set `window_length` in wotan's flatten() to ≥ 0.75 days (18 hours), which is 3× the longest expected transit duration of ~6 hours. Validate by injecting known transits and checking recovery.
**Detection:** If known planets (WASP-121b) are not detected after detrending, window length is too short.

### Anti-Pattern 2: Running MCMC on All Candidates
**What:** Running full emcee MCMC (32 walkers × 5000 steps) on every SDE ≥ 5 candidate.
**Why bad:** MCMC on 60k targets would consume hundreds of hours. Many candidates are false positives where MCMC won't converge anyway. Waste of the 30-hour window.
**Instead:** Two-gate design (see Pattern 1). Run cheap Nelder-Mead on ~50 candidates, full MCMC on top 15.

### Anti-Pattern 3: Treating Instrumental Artefacts as a Classifier Class
**What:** Adding "Instrumental/Systematic" as a 5th class to the classifier.
**Why bad:** Instrumental artefacts (momentum dumps, scattered light) are non-astrophysical and correlate with TESS quality flags — not light curve morphology. Adding them as a class dilutes training data and forces the model to learn spacecraft behaviour patterns instead of astrophysical ones.
**Instead:** Handle instrumentals as a preprocessing gate: remove quality-flagged cadences before classification. Classifier only sees astrophysical signals (4 classes). This follows ADR-0006.

### Anti-Pattern 4: Live Python Backend for Dashboard
**What:** Building a Flask/FastAPI server that runs Python inference on-demand when judges click a star in the dashboard.
**Why bad:** Requires process management, CORS configuration, error handling, and deployment complexity. If the Python process crashes during demo, the dashboard is dead. Adds 3+ hours of backend work.
**Instead:** Pre-render everything in the pipeline. Next.js reads static files from /outputs/. No Python process runs during the demo (see Pattern 2).

## Scalability Considerations

| Concern | At 3 Sectors (~60k LCs) | At 26 Sectors (~500k LCs) | At All-Sky (~1M LCs) |
|---------|--------------------------|----------------------------|----------------------|
| Data download | Async HTTP parallel, ~2h | Add batch queuing, ~8h | Need pre-downloaded archive |
| Preprocessing | Serial biweight, ~1h | Multiprocessing (Pool), ~4h | GPU-accelerated detrending |
| TLS period search | GPU CuPy, ~3h | GPU batched, ~12h | Distributed GPU cluster |
| CNN training | T4 GPU, ~2h fine-tune | Pre-trained, fine-tune per sector | Full retrain on HPC |
| MCMC parameter est. | 15 candidates, ~3h | 150 candidates, ~12h | Prioritized queue |
| Dashboard | Static site, < 100MB | Static site, ~500MB | Need lazy-loading/pagination |

## Sources

- **Pipeline architecture:** main.md Section 4 (Full Pipeline Overview)
- **AstroNet:** Shallue & Vanderburg (2018), AJ 155, 94 — Dual-View CNN architecture
- **ExoMiner++:** Valizadegan et al. (2025), AJ 170.5 — Multi-branch CNN + ensemble patterns
- **SHERLOCK:** Dévora-Pajares et al. (2024), MNRAS 532, 4752 — 6-module pipeline design
- **ADR references:** ADR-0001 (Dual-View CNN), ADR-0006 (instrumentals as gate), ADR-0008 (two-gate MCMC), ADR-0010 (Next.js read-only), ADR-0013 (mask data gaps)

---

*Architecture research for: ISRO BAH 2026 PS-07 — Exoplanet Detection Pipeline*
*Researched: 25 Jun 2026*
