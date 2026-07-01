# Phase 01: Foundation - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning

## Phase Boundary

Phase 1 delivers a batch data pipeline that downloads TESS 2-min cadence light curves for Sectors 1–3 from MAST, preprocesses ~60,000 stars (quality-masking, sigma-clipping, normalization, biweight-detrending), and runs TLS period search across all targets — producing a candidate table with SDE/SNR/CDPP per star stored in Parquet. Outputs are organized on disk for consumption by Phase 2.

## Implementation Decisions

### Pipeline Execution Model
- **D-01:** Modular step functions — separate modules for ingest, preprocess, detect, each callable independently. `run_pipeline.py` orchestrates them.
- **D-02:** Per-sector batching — process sectors sequentially, use multiprocessing within each sector for compute-heavy stages.
- **D-03:** CLI + config file — CLI for execution mode flags (`--sectors`, `--step`, `--dry-run`), YAML/JSON config for parameters (detrending window, TLS ranges, SDE thresholds).
- **D-04:** File-based checkpoints — each stage writes a checkpoint file per star/sector. On restart, skip completed stars. Critical for Colab disconnects.

### Download & Caching Strategy
- **D-05:** Pre-download all 3 sectors during the 7-day prep window. At hackathon, pipeline reads from local cache only. Eliminates MAST risk.
- **D-06:** Structured cache: `data/raw/sector{1,2,3}/` with `.npz` per TIC ID + `data/raw/catalogue.parquet`. Pipeline auto-detects cache.
- **D-07:** Retry 3× with exponential backoff on MAST failures, then skip and log the TIC ID. Pipeline runs with partial data.
- **D-08:** Exponential backoff + jitter for MAST request pacing to avoid rate-limiting.

### Disk Layout & File Naming
- **D-09:** Mirror input structure for outputs — `data/preprocessed/sector{N}/`, `data/tls/sector{N}/`. Mirrors `data/raw/` for predictable paths.
- **D-10:** Full TIC ID in filenames: `TIC_123456789_raw.npz`, `TIC_123456789_preprocessed.npz`, `TIC_123456789_tls.npz`.
- **D-11:** Single master Parquet (`data/catalogue/master.parquet`) + per-sector files (`data/catalogue/sector_1.parquet`, etc.).
- **D-12:** Keep all intermediate files on disk. Preprocessed .npz and TLS results persist for downstream phases and debugging.

### Progress Visibility & Failure Handling
- **D-13:** tqdm progress bars for real-time terminal feedback + structured JSON-lines log file (`data/logs/pipeline.log`).
- **D-14:** Skip + log + summary on per-star failures — catch exceptions, log TIC ID + error, continue. End-of-run summary reports totals.
- **D-15:** Per-star timing metrics (`download_s`, `preprocess_s`, `tls_s`) in both JSON-lines log and as columns in the Parquet catalogue.

### Agent's Discretion
- (none — user made explicit choices on all questions)

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture Decisions (ADRs)
- `docs/adr/0001-dual-view-cnn-architecture.md` — CNN over Bi-LSTM; shapes Phase 2 but Phase 1 must preserve transit shapes that CNN expects
- `docs/adr/0002-three-sector-search.md` — 3-sector scope confirmed; Phase 1 must ingest all 3
- `docs/adr/0003-synthetic-transit-injection-augmentation.md` — 7× augmentation strategy; Phase 1 preprocessing must not erase shallow (50–200 ppm) transits
- `docs/adr/0004-kepler-pretrain-tess-finetune.md` — Kepler pre-training prerequisite; Phase 1 is unaffected but Phase 2 depends on Phase 1 outputs

### Project Planning
- `.planning/PROJECT.md` — Key Decisions table (18 decisions), constraints, pre-hackathon prerequisites
- `.planning/REQUIREMENTS.md` — 55 v1 requirements; Phase 1 owns: DATA-01 through DATA-05, PREP-01 through PREP-07, DET-01 through DET-05
- `.planning/ROADMAP.md` — Phase 1 goal, 5 success criteria, dependency on nothing (first phase)

### Domain Glossary
- `CONTEXT.md` — 35 canonical terms across 6 clusters (Observational Data, Signals, Signal Classes, Detection Metrics, Classification Metrics, Stellar/Pipeline Parameters)

### Key Locked Decisions (from PROJECT.md Key Decisions table)
- Mask 13-day data gaps, do NOT interpolate (PREP-05)
- 2-tier detrending: biweight (Wotan, window_length=0.75d) for all, GP (celerite2 Matérn-3/2) for top 100 (PREP-03, PREP-04)
- TLS primary period search, BLS validation (DET-01, DET-02)
- .npz per light curve + Parquet master catalogue (DATA-05)
- 3-tier SDE gating: SDE < 5 discard, 5 ≤ SDE < 7 sub-threshold, SDE ≥ 7 full pipeline (DET-05)
- Per-star limb darkening from TICv8 (PREP-07)
- Iterative multi-planet search: 3 iterations masking found signals (DET-03)
- Instrumentals handled via TESS quality flags preprocessing gate, NOT a classifier class (PREP-01)
- Exclude stars with TESS magnitude < 6 and < 500 valid cadences (PREP-06)

## Existing Code Insights

### Reusable Assets
- No existing codebase — this is a planning-only repository. Phase 1 is the first implementation phase.

### Established Patterns
- All pipeline code will be Python 3.12 with standard scientific Python stack (NumPy, SciPy, lightkurve, astropy, astroquery).
- Prefer `.npz` + Parquet over HDF5 (per ADR decisions).
- Output directory: `/outputs/` for final deliverables, `data/` for intermediate pipeline artifacts.

### Integration Points
- Phase 1 outputs (preprocessed LCs, TLS candidate table, Parquet catalogue) are the sole input to Phase 2's feature extraction and classification.
- `run_pipeline.py --sectors 1,2,3` is the eventual single-command entry point (RPRT-04), so Phase 1 must integrate into that CLI.

## Specific Ideas

- User prefers modular, resumable pipeline with file-based checkpoints — suited for Colab sessions that may disconnect.
- Structured, predictable directory layout with sector subdirectories and TIC ID naming throughout.
- JSON-lines logging preferred for machine-parseable audit trail.

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 01-foundation-data-preprocessing-detection*
*Context gathered: 2026-06-28*
