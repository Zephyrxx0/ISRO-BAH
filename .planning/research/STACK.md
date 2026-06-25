# Technology Stack

**Project:** ISRO BAH 2026 PS-07 — Exoplanet Detection Pipeline
**Researched:** 25 Jun 2026
**Confidence:** HIGH

## Recommended Stack

### Core Language & Environment
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.10+ | Pipeline language | Entire astronomy ecosystem is Python-first. lightkurve, astropy, batman, emcee, TLS are all Python-native. Fastest iteration for hackathon. |
| Next.js | 14+ | Dashboard frontend | ISRO judges get interactive exploration of results. Pre-rendered visuals from Python pipeline — no live backend needed. Component library for candidate table + star map. |
| Node.js | 20+ | Dashboard runtime | Required by Next.js. Used only for frontend — no server-side Python bridge needed. |

### Astronomy & Data Pipeline
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `lightkurve` | 2.x | TESS data download, light curve manipulation, folding, basic BLS | NASA's official TESS/Kepler Python library. Handles MAST authentication, FITS I/O, quality masking, normalization, phase-folding. Drop-in for all data access needs. |
| `astropy` | 6.x | BLS periodogram, FITS handling, coordinate transforms, units | Foundation of the astronomy Python stack. Required by lightkurve. BLS implementation in `astropy.timeseries`. |
| `astroquery` | 0.4.x | Programmatic MAST access for bulk downloads | Queries TIC catalogue, downloads FITS files, accesses TESScut for TPF data. Handles async parallel HTTP for 4× speed improvement. |
| `wotan` | 1.x | Biweight detrending of light curves | State-of-the-art detrending library. Biweight method resists outlier influence and preserves transit shapes better than Savitzky-Golay. ~500× faster than GP, suitable for 60k LCs. |
| `celerite2` | 0.4.x | Gaussian Process red noise modelling | Matérn-3/2 kernel models correlated (red) noise structure for top 100 candidates. Only run on top candidates — too expensive for bulk. |
| `transitleastsquares` (TLS) | 1.x | Primary transit period search | Detects 10–15% more planets than BLS, especially small ones. Physically motivated model (realistic ingress/egress). Hippke & Heller (2019). |
| `batman-package` | 2.x | Mandel & Agol (2002) transit light curve model | Industry standard for transit fitting. Computes analytic transit model in milliseconds. Used for both parameter estimation and synthetic transit injection. |
| `emcee` | 3.x | MCMC ensemble sampler for parameter uncertainties | Foreman-Mackey et al. (2013). Industry standard for Bayesian parameter estimation in astronomy. 32 walkers, 5000 steps, discard 100 burn-in. |
| `corner` | 2.x | MCMC corner plot visualization | Publication-quality posterior distribution plots. Shows median + 16th/84th percentile credible intervals. |
| `eleanor` | 2.x | TESS Full Frame Image extraction | Optional. Access 30-min cadence FFI data for ~400k additional stars if time permits. Not required for primary 2-min cadence pipeline. |

### ML / AI Stack
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `tensorflow` / `keras` | 2.x | CNN classifier (AstroNet-style Dual-View 1D CNN) | Peer-reviewed architecture (Shallue & Vanderburg 2018). ISRO judges will recognize it. Simpler API than PyTorch for CNN pipelines. Auto-logging via mlflow.tensorflow. |
| `xgboost` | 2.x | Feature-based classifier (ensemble stage 2) | Gradient boosted trees on 8+ engineered features. Complements CNN's shape recognition with physics-based discriminators. Handles class imbalance natively. |
| `scikit-learn` | 1.5.x | Train/test split, cross-validation, classification metrics | Standard ML utilities. Stratified k-fold (k=5), classification_report, confusion_matrix, roc_auc_score. |
| `shap` | 0.46.x | Model explainability | TreeExplainer on XGBoost generates per-feature importance. Shows ISRO judges *why* each classification was made. No additional training needed. |
| `imbalanced-learn` | 0.12.x | Class imbalance handling | SMOTE or similar if class ratios exceed 3:1. Pipeline already uses stratified sampling, but this provides fallback. |

### Visualization
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `matplotlib` | 3.9.x | Primary plotting (light curves, phase-folded plots, periodograms) | Publication-quality static plots. Standard in astronomy. Used for 4-panel diagnostics and report figures. |
| `plotly` | 5.x | Interactive HTML exports for dashboard | Generates standalone interactive HTML files. Next.js dashboard embeds these. No Python server needed at runtime. |
| `seaborn` | 0.13.x | Confusion matrix heatmaps | Cleaner heatmaps than raw matplotlib. Used in report. |

### Utilities & Infrastructure
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `numpy` | 1.26+ | Numerical computing | Foundation of scientific Python. Required by virtually every other library. |
| `scipy` | 1.14+ | Signal processing, optimization, statistics | Used for Nelder-Mead optimization in batman fitting, statistical tests, interpolation. |
| `pandas` | 2.x | Catalog management, feature tables, candidate CSV | Columnar data for candidate catalogue. Parquet I/O. Merge TIC stellar parameters with pipeline outputs. |
| `mlflow` | 2.x | Experiment tracking, model versioning | Logs hyperparameters, metrics, model artifacts. Auto-logging via mlflow.tensorflow.autolog(). Reproducibility signal for judges. |
| `pyvo` | 1.5.x | NASA Exoplanet Archive queries | Programmatic access to confirmed planet catalog for validation targets. |
| `tqdm` | 4.x | Progress bars | User feedback during bulk processing of 60k LCs. |
| `fpdf2` | 2.7.x | PDF report generation | Generates the required 4-page PDF. Lighter than reportlab. |
| `shapely` | 2.x | Geospatial for star map | Used with folium/leaflet in Next.js dashboard to render RA/Dec star map. |

### Dashboard (Next.js)
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| Next.js | 14+ | Dashboard framework | Static export support. Reads pre-rendered JSON/HTML from /outputs/. |
| React | 18+ | UI components | Standard with Next.js. |
| Tailwind CSS | 3.x | Styling | Utility-first. Fast iteration for hackathon UI. |
| `@shadcn/ui` | latest | Component library | Pre-built table, card, badge components. Saves UI development time. |
| `leaflet` / `react-leaflet` | 4.x | Celestial star map | Render candidates on RA/Dec coordinates. Judges can click stars to see diagnostics. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Detection algorithm | TLS | BLS only | BLS uses box-shaped model; misses 10–15% of small planets. TLS uses realistic ingress/egress shape. Run both: TLS primary, BLS validation. |
| ML framework | TensorFlow/Keras | PyTorch | AstroNet reference implementation is in TensorFlow. Keras API is simpler for CNN pipelines. PyTorch proposed in submission doc for Bi-LSTM+Transformer, but CNN approach is faster to train and peer-reviewed. |
| Classifier architecture | Dual-View CNN + XGBoost | Bi-LSTM + Transformer | CNN is AstroNet peer-reviewed (Shallue & Vanderburg 2018). 1.2M vs 2.5M parameters. Faster training on T4. Bi-LSTM+Transformer is novel but riskier for a hackathon. |
| Detrending for bulk | biweight (Wotan) | Gaussian Process (bulk) | GP is ~500× slower than biweight. Running GP on 60k LCs would consume the entire hackathon. Two-tier: biweight on bulk, GP on top 100. |
| MCMC sampler | emcee | PyMC / Stan | emcee is the astronomy community standard. Used in virtually all exoplanet papers. Simpler API for transit fitting. |
| Data storage | .npz + Parquet | HDF5 | HDF5 adds dependency. .npz is zero-dependency. Parquet enables columnar querying for catalog operations. Per-star .npz isolates corruption (one bad file doesn't break everything). |
| FPP calculation | TRICERATOPS+ | VESPA | VESPA is retired and unmaintained since 2023. Community standard is now TRICERATOPS+. |
| Dashboard backend | Pre-rendered static (no Python backend) | Flask/FastAPI live backend | Live backend adds process management, CORS, deployment complexity. Pre-rendering eliminates runtime dependencies. |
| Data gap handling | Mask (don't interpolate) | Interpolation over 13-day gaps | Interpolation creates synthetic structure that TLS may falsely detect. Masking is the correct approach for transit search. |
| Limb darkening | Per-star quadratic from TICv8 | Hard-coded coefficients | Systematic depth error from fixed coefficients. Per-star interpolation is essentially free (only 15 MCMC runs). |
| GitHub research tools | Context7 + WebSearch | Shallow web search | Context7 provides curated, high-confidence documentation. WebSearch supplements for ecosystem awareness. |

## Installation

```bash
# Core pipeline (Python)
pip install lightkurve astropy astroquery batman-package emcee corner \
    tensorflow xgboost scikit-learn wotan transitleastsquares \
    celerite2 plotly shap imbalanced-learn mlflow \
    pandas pyvo tqdm fpdf2

# Optional (FFI access)
pip install eleanor

# Dashboard (Node.js)
npx create-next-app@latest dashboard --typescript --tailwind --app
cd dashboard
npm install leaflet react-leaflet @types/leaflet
npx shadcn@latest init
npx shadcn@latest add table card badge

# Verify
python -c "import lightkurve; print('OK')"
npm run dev  # Start dashboard dev server
```

## Sources

- **lightkurve:** https://docs.lightkurve.org — NASA official TESS/Kepler Python library
- **TLS:** Hippke & Heller (2019), A&A 623, A39. https://github.com/hippke/TLS
- **batman:** Mandel & Agol (2002). https://lweb.cfa.harvard.edu/~lkreidberg/batman/
- **emcee:** Foreman-Mackey et al. (2013). https://emcee.readthedocs.io
- **wotan:** https://github.com/hippke/wotan
- **celerite2:** https://celerite2.readthedocs.io
- **AstroNet:** Shallue & Vanderburg (2018), AJ 155, 94. https://github.com/google-research/exoplanet-ml
- **ExoMiner++:** Valizadegan et al. (2025), AJ 170.5. https://github.com/nasa/ExoMiner
- **TRICERATOPS+:** Gomez Barrientos et al. (2025), AJ 170:148
- **SHERLOCK:** Dévora-Pajares et al. (2024), MNRAS 532, 4752
- **Project decisions:** ADR-0001 through ADR-0019 in PROJECT.md

---

*Stack research for: ISRO BAH 2026 PS-07 — Exoplanet Detection Pipeline*
*Researched: 25 Jun 2026*
