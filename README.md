# ISRO BAH 2026 PS-07 — Exoplanet Detection Pipeline

An AI-enabled pipeline to detect, classify, and characterize exoplanets from TESS satellite light curves. Built for the ISRO Bharatiya Antariksh Hackathon 2026 Grand Finale (6–7 August 2026).

## Pipeline

```
Data Ingest → Preprocessing → Period Search (TLS) → Feature Extraction → ML Classification (CNN + XGBoost) → Parameter Estimation (MCMC) → Dashboard
```

## Quick Start

```bash
# Install Python dependencies
pip install lightkurve astropy astroquery batman-package emcee corner \
    tensorflow xgboost scikit-learn wotan transitleastsquares \
    celerite2 plotly shap mlflow pandas tqdm fpdf2 pyvo

# Install dashboard dependencies
pnpm install --dir SPACE

# Run pipeline
python pipeline/run_pipeline.py --sectors 1,2,3 --presentation

# Serve dashboard
make serve
```

## Architecture

- **Detection**: TLS primary (10–15% more small planets than BLS) with BLS validation
- **Classification**: Dual-View CNN (AstroNet) + XGBoost ensemble, 4-class (Planet Candidate, Eclipsing Binary, Background Blend, Stellar Variability)
- **Training**: Kepler DR24 pre-training → TESS ExoFOP fine-tuning
- **Parameters**: Two-gate MCMC — Nelder-Mead batman fit → emcee on top candidates
- **Validation**: TRICERATOPS+ FPP/NFPP, SHERLOCK benchmark, known planet recovery tests
- **Dashboard**: Next.js 15 (App Router) with pre-rendered static exports, Plotly.js, Leaflet.js

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| ML/DL | TensorFlow 2.21 (Keras), XGBoost 3.3, scikit-learn 1.7 |
| Astronomy | lightkurve, astropy, astroquery, TLS, batman, emcee, celerite2 |
| Dashboard | Next.js 15, shadcn/ui, Tailwind 4, Plotly.js, Leaflet.js |
| Storage | `.npz` per light curve + Parquet master catalogue |

## Project Structure

```
.planning/         # Project plans, requirements, roadmap, ADRs
docs/adr/          # Architecture Decision Records
pipeline/          # Main orchestration & ingestion
src/               # ML, characterization, visualization, validation
SPACE/             # Next.js dashboard
tests/             # pytest suite
outputs/           # Generated plots, JSON, catalogues
```

## Validation Targets

| Target | System | Period |
|--------|--------|--------|
| WASP-121b (TIC 22529346) | Hot Jupiter | 1.27 d |
| TOI-270 (TIC 259377017) | 3 super-Earths | 3.36, 5.66, 11.38 d |
| L 98-59 (TIC 307210830) | 3 small planets | 2.25, 3.69, 7.45 d |

## License

MIT
