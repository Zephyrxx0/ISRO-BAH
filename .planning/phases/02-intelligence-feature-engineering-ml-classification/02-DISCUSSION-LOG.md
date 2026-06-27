# Phase 02: Intelligence - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-28
**Phase:** 02-intelligence-feature-engineering-ml-classification
**Areas discussed:** Training pipeline organization, Feature extraction module design, Ensemble & calibration wiring, Phase 1→2 data contract

---

## Training Pipeline Organization

### Q1: Kepler pre-training script vs main pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone pre-training script | Separate `train_kepler.py` runs during prep week, saves weights to disk | ✓ |
| Single script with mode flag | One `train.py --mode pretrain\|finetune` | |
| Integrated pipeline step | Part of `run_pipeline.py` as `--step train` | |

**User's choice:** Standalone pre-training script (Recommended)
**Notes:** Clean separation between prep-week pre-training and hackathon fine-tuning. No risk of accidentally re-running pre-training during event.

### Q2: XGBoost training alongside or separate from CNN

| Option | Description | Selected |
|--------|-------------|----------|
| Separate XGBoost training script | `train_xgboost.py` runs after feature extraction | ✓ |
| Combined CNN+XGBoost script | Single `train_ensemble.py` for both | |
| Pipeline step via run_pipeline.py | `run_pipeline.py --step train` | |

**User's choice:** Separate XGBoost training script (Recommended)
**Notes:** Decouples XGBoost from CNN — team members can split work, different hardware possible.

### Q3: Model weights storage and fine-tuning invocation

| Option | Description | Selected |
|--------|-------------|----------|
| Models directory + dedicated fine-tune script | `data/models/kepler_pretrained.h5`, separate `train_cnn_finetune.py` | ✓ |
| Models directory, integrated fine-tune | Same paths but `train.py --mode finetune` | |
| Pipeline-managed paths | Weights under `data/models/`, loaded by pipeline orchestration | |

**User's choice:** Models directory + dedicated fine-tune script (Recommended)
**Notes:** Pre-trained weights: `data/models/kepler_pretrained.h5`. CNN fine-tuned: `data/models/cnn_finetuned.h5`. XGBoost: `data/models/xgboost_ensemble.json`.

### Q4: Augmentation integration strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Keras data generator with augmentation | `tf.keras.utils.Sequence` applies augmentations on-the-fly | ✓ |
| Pre-generate augmented .npz files | Separate preprocessing step writes augmented files to disk | |
| Let agent decide | | |

**User's choice:** Keras data generator with augmentation (Recommended)
**Notes:** Augmented samples generated during fit(), not pre-saved. Saves disk space (~85k samples × 201 points). Matches Keras best practices.

---

## Feature Extraction Module Design

### Q1: Feature extraction structure

| Option | Description | Selected |
|--------|-------------|----------|
| Class-based extractor | `FeatureExtractor` class per TIC ID + separate `CentroidAnalyzer` | ✓ |
| Batch/vectorized processor | Load all candidates, vectorized NumPy | |
| Let agent decide | | |

**User's choice:** Class-based extractor (Recommended)
**Notes:** Matches Phase 1's modular pattern. Clean, testable. TPF centroid analysis as separate class.

### Q2: Phase-folding placement

| Option | Description | Selected |
|--------|-------------|----------|
| Separate phase-folding step | `PhaseFolder` class, saves `TIC_ID_folded.npz` per candidate | ✓ |
| Inside feature extractor | Fold on-the-fly during feature computation | |
| Let agent decide | | |

**User's choice:** Separate phase-folding step (Recommended)
**Notes:** Both feature extractor and CNN inference read same folded files — no recomputation. Matches Phase 1 keep-intermediates pattern.

### Q3: TPF centroid analysis scope

| Option | Description | Selected |
|--------|-------------|----------|
| Top 200 SDE≥7 only, separate download | Download TPFs via TESScut during feature extraction | ✓ |
| Pre-download all TPFs for Sectors 1-3 | ~500GB — impractical for Colab | |
| Phase 1 downloads TPFs with light curves | Requires Phase 1 replanning | |

**User's choice:** Top 200 SDE≥7 only, separate download (Recommended)
**Notes:** Avoids downloading 60k TPFs (~500GB). Matches FEAT-02 spec (centroid shift on top candidates).

### Q4: Feature storage destination

| Option | Description | Selected |
|--------|-------------|----------|
| Append to master Parquet catalogue | Feature columns in `data/catalogue/master.parquet` | ✓ |
| Separate features.parquet | Join on TIC ID | |
| .npz per candidate | `TIC_ID_features.npz` | |

**User's choice:** Append to master Parquet catalogue (Recommended)
**Notes:** Single source of truth. XGBoost, ensemble, and Phase 3 all read from same catalogue. No joins needed.

---

## Ensemble & Calibration Wiring

### Q1: CNN + XGBoost combination mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated EnsemblePredictor class | Loads both models, runs inference independently, weighted average | ✓ |
| Unified ensemble pipeline step | Orchestrates both sequentially | |
| Train a meta-learner | Logistic regression on top of both | |

**User's choice:** Dedicated EnsemblePredictor class (Recommended)
**Notes:** One model failure doesn't block the other. Independent inference.

### Q2: Data split for training/calibration/evaluation

| Option | Description | Selected |
|--------|-------------|----------|
| 3-way split: train/cal/test | 60% train / 20% calibration / 20% test | ✓ |
| Cross-validation with holdout | K-fold + final holdout | |
| Train/test only, calibrate on test | Biased metrics | |
| Let agent decide | | |

**User's choice:** 3-way split: train/cal/test (Recommended)
**Notes:** Calibration set for temperature scaling; test set untouched for unbiased CLAS-06 evaluation.

### Q3: Temperature scaling implementation

| Option | Description | Selected |
|--------|-------------|----------|
| scikit-learn + numpy | Logistic regression on logits or direct formula (~10 lines) | ✓ |
| NetCal / Calibration library | Extra dependency | |
| Custom TF/Keras layer | Couples calibration to CNN only | |

**User's choice:** scikit-learn + numpy (Recommended)
**Notes:** Lightweight, no extra dependency. Temperature T learned via LBFGS on calibration set.

### Q4: Confidence tier basis

| Option | Description | Selected |
|--------|-------------|----------|
| PC softmax probability | Confidence = ensemble softmax[PC_class] | ✓ |
| Entropy-based confidence | 1 − normalized_entropy(softmax) | |
| Max softmax (any class) | Confidence = max(softmax) | |

**User's choice:** PC softmax probability (Recommended)
**Notes:** Directly interpretable as "probability this is a planet candidate". Gold >0.90, Silver 0.70–0.90, Bronze <0.70.

**Additional note:** User specified CuPy should be preferred over NumPy when GPU available for array operations.

---

## Phase 1→2 Data Contract

### Q1: Preprocessed .npz schema

| Option | Description | Selected |
|--------|-------------|----------|
| Standardized .npz schema | Fixed keys: time, flux, flux_raw, flux_err, quality_mask, sector, tic_id | ✓ |
| Flexible .npz with metadata header | JSON metadata key + arrays | |
| lightkurve LightCurve object serialized | Ties Phase 2 to lightkurve objects | |

**User's choice:** Standardized .npz schema (Recommended)
**Notes:** Predictable. Phase 2 reads with `np.load()` and accesses by key.

### Q2: Parquet column specification

| Option | Description | Selected |
|--------|-------------|----------|
| Contract schema document | `data/catalogue/schema.md` defines required columns | ✓ |
| Ad-hoc: Phase 2 reads what Phase 1 writes | Fragile — rename breaks Phase 2 | |
| Shared dataclass in utils/ | `utils/catalogue_schema.py` used by both phases | |

**User's choice:** Contract schema document (Recommended)
**Notes:** Required columns: tic_id, sector, tess_mag, ra, dec, candidate_num, tls_period, tls_t0, tls_sde, tls_snr, tls_cdpp, tls_depth, tls_duration, n_valid_cadences, preprocessed_path.

### Q3: Phase 1 output validation

| Option | Description | Selected |
|--------|-------------|----------|
| Input validation step | `validate_phase1_outputs()` checks catalogue, .npz paths, keys, candidate count | ✓ |
| Fail fast on first missing file | Opaque errors | |
| Skip validation, document requirements | Risk in hackathon conditions | |

**User's choice:** Input validation step (Recommended)
**Notes:** Runs as first step of Phase 2 pipeline. Reports missing/invalid without crashing.

### Q4: Multi-candidate representation in catalogue

| Option | Description | Selected |
|--------|-------------|----------|
| One row per candidate | Same TIC ID appears multiple times with candidate_num column | ✓ |
| One row per star, candidates as arrays | Parquet list columns harder to query | |
| Separate candidates.parquet | Cleaner normalization but adds join | |

**User's choice:** One row per candidate (Recommended)
**Notes:** Each row = one TLS detection. Phase 2 classifies each independently. candidate_num (1,2,3) distinguishes multi-planet systems.

---

## Agent's Discretion

None — user made explicit choices on all questions.

## Deferred Ideas

None — discussion stayed within phase scope.
