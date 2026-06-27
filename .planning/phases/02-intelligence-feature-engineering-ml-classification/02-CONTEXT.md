# Phase 02: Intelligence - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning

## Phase Boundary

Phase 2 takes Phase 1's TLS candidates (SDE≥5, ~60k stars) and preprocessed light curves, extracts 8+ engineered features per candidate (odd/even depth, centroid shift, V-shape, CROWDSAP, secondary eclipse depth, duration/period ratio, SDE, SNR), trains a Dual-View CNN (Kepler DR24 pre-trained → TESS ExoFOP fine-tuned with 7× augmentation) and XGBoost classifier, produces a 4-class ensemble (0.6×CNN + 0.4×XGBoost) with temperature-scaled confidence scores (ECE < 0.04), and assigns Gold/Silver/Bronze tiers. All results appended to the master Parquet catalogue. MLflow tracks both training experiments.

## Implementation Decisions

### Training Pipeline Organization
- **D-01:** Separate standalone `train_kepler.py` for Kepler DR24 pre-training — runs during prep week only, saves to `data/models/kepler_pretrained.h5`. Must NOT run during hackathon.
- **D-02:** Separate `train_cnn_finetune.py` for TESS fine-tuning — loads `kepler_pretrained.h5` during hackathon. Separate from pre-training to enforce prep-week vs hackathon boundary.
- **D-03:** Separate `train_xgboost.py` for XGBoost training — runs after feature extraction completes during hackathon. Decoupled from CNN training.
- **D-04:** Keras data generator (`tf.keras.utils.Sequence`) applies 7× augmentation (noise injection + transit jitter + synthetic transit injection at 50–200 ppm) on-the-fly during training. No pre-generated augmented files.
- **D-05:** All model artifacts saved to `data/models/`: `kepler_pretrained.h5`, `cnn_finetuned.h5`, `xgboost_ensemble.json`.

### Feature Extraction Module Design
- **D-06:** Class-based `FeatureExtractor` — takes TIC ID, loads preprocessed .npz + catalogue row, returns feature vector. Separate `CentroidAnalyzer` class for TPF-based analysis.
- **D-07:** Prefer CuPy over NumPy for GPU-accelerated array operations in feature extraction and phase-folding.
- **D-08:** Separate `PhaseFolder` class — generates 2001-point global + 201-point local phase-folded views, saves as `TIC_ID_folded.npz` per candidate. Both feature extractor and CNN inference read from same folded files (no recomputation).
- **D-09:** TPF-based centroid analysis: download TPFs via TESScut for top 200 SDE≥7 candidates only (not all 60k). `CentroidAnalyzer` computes flux-weighted centroid shift in-transit vs out-of-transit; shift > 3σ flags blend.
- **D-10:** Extracted features appended as new columns to `data/catalogue/master.parquet`. Single source of truth — XGBoost, ensemble, and Phase 3 all read from the same catalogue.

### Ensemble & Calibration Wiring
- **D-11:** Dedicated `EnsemblePredictor` class — loads CNN model + XGBoost model, runs inference independently, combines via weighted average (0.6×CNN + 0.4×XGBoost). One model failure doesn't block the other.
- **D-12:** 3-way stratified data split: 60% train / 20% calibration / 20% test. Calibration set used for temperature scaling only; test set untouched for final CLAS-06 evaluation.
- **D-13:** Temperature scaling via scikit-learn logistic regression on logits (or direct NumPy formula). Single temperature T learned on calibration set via LBFGS.
- **D-14:** Confidence = PC class softmax probability from calibrated ensemble. Gold > 0.90, Silver 0.70–0.90, Bronze < 0.70.

### Phase 1→2 Data Contract
- **D-15:** Standardized .npz schema per preprocessed light curve — required keys: `time` (BJD), `flux` (normalized, detrended), `flux_raw` (pre-detrending), `flux_err`, `quality_mask` (boolean), `sector`, `tic_id`.
- **D-16:** Contract schema document (`data/catalogue/schema.md`) defines required Parquet columns: `tic_id`, `sector`, `tess_mag`, `ra`, `dec`, `candidate_num`, `tls_period`, `tls_t0`, `tls_sde`, `tls_snr`, `tls_cdpp`, `tls_depth`, `tls_duration`, `n_valid_cadences`, `preprocessed_path`. One row per candidate (same TIC ID can appear multiple times).
- **D-17:** Phase 2 input validation step (`validate_phase1_outputs()`) — checks catalogue exists with required columns, all referenced .npz paths exist, sample .npz files load with required keys, SDE≥5 candidate count > 0. Reports missing/invalid without crashing.

### Agent's Discretion
- (none — user made explicit choices on all questions)

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture Decisions (ADRs)
- `docs/adr/0001-dual-view-cnn-architecture.md` — CNN architecture (AstroNet), 2001+201 views, 4-class softmax output
- `docs/adr/0002-three-sector-search.md` — 3-sector scope, cross-sector validation
- `docs/adr/0003-synthetic-transit-injection-augmentation.md` — 7× augmentation strategy, synthetic transit injection depths
- `docs/adr/0004-kepler-pretrain-tess-finetune.md` — Kepler DR24 pre-training prerequisite, TESS fine-tuning approach

### Project Planning
- `.planning/PROJECT.md` — Key Decisions table (18 decisions), constraints, stack
- `.planning/REQUIREMENTS.md` — Phase 2 owns: FEAT-01 through FEAT-04, CLAS-01 through CLAS-07, CONF-01 through CONF-03, MLOP-01, MLOP-02
- `.planning/ROADMAP.md` — Phase 2 goal, 5 success criteria, dependency on Phase 1
- `.planning/phases/01-foundation-data-preprocessing-detection/01-CONTEXT.md` — Phase 1 decisions: directory layout, file naming, checkpoint pattern (modular step functions, tqdm, JSON-lines logging)

### Data Contract
- `data/catalogue/schema.md` — Parquet column specification (to be created by Phase 1, referenced by Phase 2)

### Domain Glossary
- `CONTEXT.md` — 35 canonical terms (Observational Data, Signals, Signal Classes, Detection Metrics, Classification Metrics, Stellar/Pipeline Parameters)

## Existing Code Insights

### Reusable Assets
- No existing codebase — Phase 1 is under development. Phase 2 will be the second implementation phase.

### Established Patterns
- Modular step functions with file-based checkpoints (Phase 1 pattern)
- Structured directory layout: `data/raw/sector{N}/`, `data/preprocessed/sector{N}/`, `data/tls/sector{N}/`
- .npz per TIC ID + Parquet master catalogue
- tqdm progress bars + JSON-lines logging
- `run_pipeline.py` CLI entry point (Phase 2 modules integrate here)

### Integration Points
- Phase 2 reads from Phase 1 outputs: `data/preprocessed/sector{N}/TIC_*_preprocessed.npz` and `data/catalogue/master.parquet`
- Phase 2 writes to: `data/catalogue/master.parquet` (appends feature columns), `data/folded/` (phase-folded views), `data/models/` (trained model artifacts), `data/tpf/` (downloaded TPFs)
- Phase 3 consumes Phase 2 outputs: classification labels, confidence scores, feature columns in Parquet

## Specific Ideas

- CuPy preferred over NumPy when GPU available for array operations (feature extraction, phase-folding) — accelerates batch computations on Colab T4
- All training scripts are standalone (not integrated into `run_pipeline.py` steps) — training is a manual, once-per-event activity
- Feature columns appended to master Parquet rather than separate files — keeps catalogue as single source of truth for all downstream consumers

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 02-intelligence-feature-engineering-ml-classification*
*Context gathered: 2026-06-28*
