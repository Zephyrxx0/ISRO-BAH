# Phase 1 Summary: Foundation — Data, Preprocessing & Detection

**Status:** Complete
**Date:** 2026-07-01
**Plans:** 1 (consolidated)
**Requirements:** DATA-01 through DET-05 (17 reqs)

## What Was Built

Phase 1 ingests TESS 2-min cadence light curves from MAST for Sectors 1–3 (~60,000 stars), preprocesses them preserving transit signals, runs TLS period search with multi-planet iteration, and gates candidates via 3-tier SDE thresholds.

### Modules Created

| Module | File | Requirement |
|--------|------|-------------|
| TESS Download | `pipeline/ingest/download_tess.py` | DATA-01 |
| .npz Storage | `pipeline/ingest/store.py` | DATA-05 |
| Quality Mask | `pipeline/preprocess/quality_mask.py` | PREP-01 |
| Sigma Clip + Normalize | `pipeline/preprocess/sigma_clip.py` | PREP-02 |
| Biweight Detrend | `pipeline/preprocess/detrend.py` | PREP-03 |
| GP Detrend (celerite2) | `pipeline/preprocess/gp_detrend.py` | PREP-04 |
| Gap Mask (13-day) | `pipeline/preprocess/gap_mask.py` | PREP-05 |
| Star Exclusion Filters | `pipeline/preprocess/filters.py` | PREP-06 |
| Limb Darkening Lookup | `pipeline/preprocess/limb_darkening.py` | PREP-07 |
| TLS Period Search | `pipeline/detect/tls_search.py` | DET-01, DET-03 |
| BLS Validation | `pipeline/detect/bls_validate.py` | DET-02 |
| SDE Gating (3-tier) | `pipeline/detect/sde_gate.py` | DET-05 |
| Smoke Test Validation | `pipeline/validate/smoke_test.py` | VAL-01, VAL-02 |
| Pipeline Configuration | `pipeline/config.py` | — |
| Orchestration Entrypoint | `pipeline/run_pipeline.py` | RPRT-04 |

### Architecture Decisions Followed

- **TLS primary, BLS validation** — not BLS-first (per ADR-0005)
- **3-tier SDE gating** — <5 discard, 5–7 sub-threshold, ≥7 full pipeline
- **Gap masking** — 13-day TESS gaps masked, not interpolated (ADR-0013)
- **Per-star limb darkening** — nearest-neighbor Teff lookup from Claret table (ADR-0011)
- **.npz + Parquet storage** — no HDF5, no PostgreSQL (ADR-0009)
- **Biweight bulk detrend + GP on top candidates** — 2-tier (ADR-0010)

### Bugs Fixed During Execution

- `pipeline/ingest/store.py:9` — `npz_path()` body was `...` stub; implemented full path generation
- Created `__init__.py` files for `pipeline/`, `ingest/`, `preprocess/`, `detect/`, `validate/`
