# Phase 2: Intelligence — Pattern Map

**Generated:** 2026-06-28
**Phase:** Feature Engineering & ML Classification
**Status:** No existing code — patterns derived from Phase 1 conventions + RESEARCH.md architecture

---

## Module Structure (src/phase2/)

```
src/phase2/
├── __init__.py                  # Package init, version string
├── validate_phase1.py           # Input validation gate
├── phase_folder.py              # PhaseFolder class
├── feature_extractor.py         # FeatureExtractor class
├── centroid_analyzer.py         # CentroidAnalyzer (TPF-based)
├── data_generator.py            # TransitDataGenerator (tf.keras.utils.Sequence)
├── model.py                     # build_astronet_dual_view() factory
├── train_kepler.py              # Standalone: Kepler DR24 pre-training
├── train_cnn_finetune.py        # Standalone: TESS ExoFOP fine-tuning
├── train_xgboost.py             # Standalone: XGBoost classifier
├── temperature_scaler.py        # TemperatureScaler class
├── ensemble_predictor.py        # EnsemblePredictor class
├── evaluate.py                  # Full evaluation suite (metrics + plots)
└── pipeline_integration.py      # run_phase2() hook for run_pipeline.py
```

---

## File Catalog — Role, Data Flow, Dependencies

### 1. `validate_phase1.py`

| Attribute | Value |
|-----------|-------|
| **Role** | Input validation gate — first step of Phase 2 |
| **Reads** | `data/catalogue/master.parquet`, sampled `data/preprocessed/sector{N}/TIC_*_preprocessed.npz` |
| **Writes** | Nothing (raises on failure, prints summary on success) |
| **Depends on** | `pandas`, `numpy`, `pathlib` |
| **Called by** | `pipeline_integration.py` (step 1) |
| **Pattern** | Pure function: `validate_phase1_outputs(catalogue_path) → None | raises ValueError` |

### 2. `phase_folder.py`

| Attribute | Value |
|-----------|-------|
| **Role** | Generate 2001-global + 201-local phase-folded views per candidate |
| **Reads** | `data/preprocessed/sector{N}/TIC_*_preprocessed.npz`, rows from `master.parquet` (period, t0, duration) |
| **Writes** | `data/folded/TIC_{id}_folded.npz` (keys: `global`, `local`); updates `folded_path` column in Parquet |
| **Depends on** | `numpy`/`cupy`, `pandas`, `tqdm`, `pathlib` |
| **Called by** | `pipeline_integration.py` (step 2) |
| **Pattern** | Class `PhaseFolder` with `run_all()` batch method + `fold_single()` per-star method |

### 3. `feature_extractor.py`

| Attribute | Value |
|-----------|-------|
| **Role** | Compute 8 engineered features per SDE≥5 candidate |
| **Reads** | `data/preprocessed/sector{N}/TIC_*_preprocessed.npz`, `data/folded/TIC_{id}_folded.npz`, `master.parquet` |
| **Writes** | Appends 8 feature columns to `data/catalogue/master.parquet` |
| **Depends on** | `numpy`/`cupy`, `pandas`, `tqdm`, `pathlib` |
| **Called by** | `pipeline_integration.py` (step 3) |
| **Pattern** | Class `FeatureExtractor` with `run_all()` + `_extract_single(row)` returning feature dict |

### 4. `centroid_analyzer.py`

| Attribute | Value |
|-----------|-------|
| **Role** | TPF-based centroid shift analysis for top 200 SDE≥7 candidates |
| **Reads** | `master.parquet` (to select top 200), TPFs downloaded via TESScut/lightkurve |
| **Writes** | Updates `centroid_shift_sigma` column in `master.parquet`; caches TPFs to `data/tpf/` |
| **Depends on** | `lightkurve`, `numpy`, `pandas`, `tqdm` |
| **Called by** | `pipeline_integration.py` (step 3b, parallelizable with feature extraction) |
| **Pattern** | Class `CentroidAnalyzer` with `run_top_n(n=200)` + `compute_centroid_shift(tpf, transit_mask)` |

### 5. `data_generator.py`

| Attribute | Value |
|-----------|-------|
| **Role** | On-the-fly 7× augmented data loading for CNN training |
| **Reads** | `data/folded/TIC_{id}_folded.npz` (via paths in training DataFrame) |
| **Writes** | Nothing (yields batches to model.fit) |
| **Depends on** | `tensorflow`, `numpy`, `batman`, `pandas` |
| **Called by** | `train_cnn_finetune.py` |
| **Pattern** | Class `TransitDataGenerator(tf.keras.utils.Sequence)` with `__getitem__`, `_augment` |

### 6. `model.py`

| Attribute | Value |
|-----------|-------|
| **Role** | CNN model factory — build_astronet_dual_view() |
| **Reads** | Nothing (pure construction) |
| **Writes** | Nothing (returns tf.keras.Model) |
| **Depends on** | `tensorflow` |
| **Called by** | `train_kepler.py`, `train_cnn_finetune.py` |
| **Pattern** | Pure function: `build_astronet_dual_view(global_len, local_len, num_classes) → Model` |

### 7. `train_kepler.py`

| Attribute | Value |
|-----------|-------|
| **Role** | Standalone prep-week script — pre-train CNN on Kepler DR24 |
| **Reads** | `data/kepler/kepler_dr24_folded.npz` (pre-prepared Kepler views) |
| **Writes** | `data/models/kepler_pretrained.h5` |
| **Depends on** | `tensorflow`, `sklearn`, `numpy`, `mlflow`, `model.py` |
| **Called by** | Manual execution only (NOT part of run_pipeline.py) |
| **Pattern** | Standalone script with `if __name__ == '__main__':` — no class, direct execution |

### 8. `train_cnn_finetune.py`

| Attribute | Value |
|-----------|-------|
| **Role** | Standalone hackathon script — fine-tune pre-trained CNN on TESS ExoFOP labels |
| **Reads** | `data/models/kepler_pretrained.h5`, `data/folded/`, ExoFOP labels (from `master.parquet` or separate CSV) |
| **Writes** | `data/models/cnn_finetuned.h5` |
| **Depends on** | `tensorflow`, `sklearn`, `numpy`, `mlflow`, `data_generator.py`, `model.py` |
| **Called by** | Manual execution only |
| **Pattern** | Standalone script — loads base model, freezes early layers, trains with TransitDataGenerator |

### 9. `train_xgboost.py`

| Attribute | Value |
|-----------|-------|
| **Role** | Standalone hackathon script — train XGBoost on extracted features |
| **Reads** | `data/catalogue/master.parquet` (feature columns + labels) |
| **Writes** | `data/models/xgboost_ensemble.json` |
| **Depends on** | `xgboost`, `sklearn`, `numpy`, `pandas`, `mlflow`, `shap` |
| **Called by** | Manual execution only |
| **Pattern** | Standalone script — loads features from Parquet, stratified split, trains, logs to MLflow |

### 10. `temperature_scaler.py`

| Attribute | Value |
|-----------|-------|
| **Role** | Learn + apply temperature scaling for ensemble calibration |
| **Reads** | Calibration set logits (from CNN + XGBoost on held-out 20%) |
| **Writes** | `data/models/temperature_scalar.npz` |
| **Depends on** | `numpy`, `scipy` |
| **Called by** | Training workflow (after both models trained); `ensemble_predictor.py` (at inference) |
| **Pattern** | Class `TemperatureScaler` with `fit(logits, labels)`, `predict_proba(logits)`, `save()`, `load()` |

### 11. `ensemble_predictor.py`

| Attribute | Value |
|-----------|-------|
| **Role** | Load both models + scaler, produce calibrated 4-class predictions |
| **Reads** | `data/models/cnn_finetuned.h5`, `data/models/xgboost_ensemble.json`, `data/models/temperature_scalar.npz`, `data/folded/`, `master.parquet` |
| **Writes** | Appends classification columns to `master.parquet` (`predicted_class`, `confidence_pc`, `prob_EB`, `prob_Blend`, `prob_StellarVar`, `confidence_tier`) |
| **Depends on** | `tensorflow`, `xgboost`, `numpy`, `pandas`, `tqdm`, `temperature_scaler.py` |
| **Called by** | `pipeline_integration.py` (step 4) |
| **Pattern** | Class `EnsemblePredictor` with `classify_all(catalogue_path)` + `predict_single(...)` |

### 12. `evaluate.py`

| Attribute | Value |
|-----------|-------|
| **Role** | Compute all evaluation metrics (accuracy, F1-macro, recall, FPR, ECE, ROC-AUC) + generate plots |
| **Reads** | `master.parquet` (predictions + ground-truth labels on test set) |
| **Writes** | `outputs/confusion_matrix.png`, `outputs/reliability.png`, `outputs/shap_summary.png`, metric summaries to MLflow |
| **Depends on** | `sklearn`, `matplotlib`, `shap`, `mlflow`, `numpy`, `pandas` |
| **Called by** | Manual (post-training) or `pipeline_integration.py` (step 5) |
| **Pattern** | Function-based: `run_evaluation(catalogue_path, model_dir)` → prints pass/fail per metric |

### 13. `pipeline_integration.py`

| Attribute | Value |
|-----------|-------|
| **Role** | Orchestrator — wires Phase 2 steps into `run_pipeline.py` |
| **Reads** | Config (sectors, model paths) |
| **Writes** | Nothing directly (delegates to other modules) |
| **Depends on** | All other Phase 2 modules |
| **Called by** | `run_pipeline.py --step phase2` |
| **Pattern** | Single function `run_phase2(catalogue_path, sectors, model_dir)` — sequential step calls |

---

## Data Flow Diagram

```
Phase 1 Outputs
│
├── data/catalogue/master.parquet (tic_id, tls_period, tls_t0, tls_sde, ...)
├── data/preprocessed/sector{N}/TIC_*_preprocessed.npz
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│  validate_phase1.py  →  checks existence + schema + SDE≥5 count    │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  phase_folder.py  →  data/folded/TIC_{id}_folded.npz               │
│    (reads .npz time/flux + Parquet period/t0/duration)              │
└─────────────────────────────────────────────────────────────────────┘
         │
         ├──────────────────────────────┐
         ▼                              ▼
┌────────────────────────┐   ┌──────────────────────────────┐
│  feature_extractor.py  │   │  centroid_analyzer.py        │
│  → 8 cols in Parquet   │   │  → centroid_shift_sigma col  │
└────────────────────────┘   └──────────────────────────────┘
         │                              │
         └──────────────┬───────────────┘
                        ▼
         ┌──── TRAINING (manual, standalone) ────┐
         │                                       │
         ▼                                       ▼
┌──────────────────────┐              ┌─────────────────────┐
│  train_cnn_finetune  │              │  train_xgboost.py   │
│  (uses data_gen +    │              │  (uses Parquet      │
│   kepler_pretrained) │              │   feature cols)     │
│  → cnn_finetuned.h5  │              │  → xgboost.json     │
└──────────────────────┘              └─────────────────────┘
         │                                       │
         └───────────────┬───────────────────────┘
                         ▼
         ┌───────────────────────────────────────┐
         │  temperature_scaler.py                │
         │  (learns T on 20% calibration set)    │
         │  → temperature_scalar.npz             │
         └───────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────────┐
         │  ensemble_predictor.py                │
         │  (0.6×CNN + 0.4×XGB, temp-scaled)    │
         │  → classification cols in Parquet     │
         └───────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────────┐
         │  evaluate.py                          │
         │  → metrics, plots, pass/fail gate     │
         └───────────────────────────────────────┘
                         │
                         ▼
              Phase 3 reads: Gold-tier candidates
```

---

## Coding Conventions (from Phase 1 Patterns)

### 1. Modular Step Functions

Each processing stage is an independent module callable in isolation. The orchestrator (`pipeline_integration.py`) calls them sequentially, but any module can run standalone for debugging.

```python
# Pattern: Class with run_all() batch entry + per-item method
class PhaseFolder:
    def __init__(self, catalogue_path, preprocessed_dir, folded_dir):
        ...

    def run_all(self):
        """Process all SDE≥5 candidates. Skips already-folded (checkpoint)."""
        ...

    def fold_single(self, time, flux, period, t0, duration):
        """Pure computation for one star. Returns (global_view, local_view)."""
        ...
```

### 2. File-Based Checkpoints

Each stage writes per-star output files. On re-run, skip stars whose output already exists. Critical for Colab session recovery.

```python
# Pattern: skip if output exists
output_path = Path(f'data/folded/TIC_{tic_id}_folded.npz')
if output_path.exists():
    continue  # already processed
```

### 3. Progress + Logging

tqdm for terminal progress bars. JSON-lines structured log for audit trail.

```python
import json
from tqdm import tqdm

for idx in tqdm(candidates.index, desc='Phase-folding'):
    ...
    # JSON-lines log entry
    log_entry = {'tic_id': tic_id, 'step': 'fold', 'status': 'ok', 'elapsed_s': elapsed}
    with open('data/logs/phase2.log', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
```

### 4. Error Handling — Skip + Log + Continue

Per-star failures don't crash the pipeline. Catch, log, continue. Report totals at end.

```python
# Pattern: graceful per-star error handling
errors = []
for idx in tqdm(candidates.index):
    try:
        result = self._extract_single(candidates.loc[idx])
    except Exception as e:
        errors.append({'tic_id': candidates.loc[idx]['tic_id'], 'error': str(e)})
        continue

if errors:
    print(f'⚠ {len(errors)}/{len(candidates)} stars failed. See log.')
```

### 5. Storage Conventions

| Data Type | Format | Location |
|-----------|--------|----------|
| Per-star time series | `.npz` | `data/preprocessed/sector{N}/`, `data/folded/` |
| Tabular catalogue | Parquet | `data/catalogue/master.parquet` |
| Model artifacts | `.h5` (Keras), `.json` (XGBoost), `.npz` (scaler) | `data/models/` |
| Diagnostic plots | PNG | `outputs/` |
| Logs | JSON-lines | `data/logs/phase2.log` |

### 6. Naming Conventions

- Files: `TIC_{full_id}_{stage}.npz` (e.g., `TIC_123456789_folded.npz`)
- Modules: snake_case, descriptive (`feature_extractor.py`, not `fe.py`)
- Classes: PascalCase matching module name (`FeatureExtractor` in `feature_extractor.py`)
- Functions: snake_case verb-noun (`compute_odd_even_depth`, `validate_phase1_outputs`)
- Constants: UPPER_SNAKE (`CNN_WEIGHT = 0.6`, `FEATURE_COLUMNS = [...]`)

### 7. GPU/CuPy Pattern

Prefer CuPy when available (D-07), fall back to NumPy transparently.

```python
try:
    import cupy as cp
    xp = cp
except ImportError:
    import numpy as np
    xp = np
```

### 8. Training Scripts — Standalone Pattern

Training scripts are NOT part of the pipeline orchestrator. They are manual, one-shot scripts with their own `if __name__ == '__main__':` entry points, MLflow logging, and CLI args.

```python
# Pattern: standalone training script
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fine-tune CNN on TESS ExoFOP')
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--lr', type=float, default=1e-4)
    args = parser.parse_args()

    mlflow.set_tracking_uri(f'file://{os.getcwd()}/.mlruns')
    mlflow.set_experiment('tess-finetune-xgboost')
    with mlflow.start_run(run_name='cnn-finetune'):
        mlflow.log_params(vars(args))
        # ... training logic ...
```

### 9. Mixed Precision Pattern (Mandatory for T4)

```python
from tensorflow.keras import mixed_precision
mixed_precision.set_global_policy('mixed_float16')
# ALWAYS: final Dense layer uses dtype='float32' to prevent softmax precision loss
```

### 10. MLflow Logging Pattern

Local filesystem tracking, no server. Manual logging (no autolog).

```python
import mlflow

mlflow.set_tracking_uri(f'file://{os.getcwd()}/.mlruns')
mlflow.set_experiment('experiment-name')
with mlflow.start_run(run_name='descriptive-run-name'):
    mlflow.set_tag('phase', '2-intelligence')
    mlflow.log_params({...})
    mlflow.log_metrics({...}, step=epoch)
    mlflow.log_artifact('path/to/model.h5')
```

---

## Dependency Matrix

| Module | Internal Deps | External Packages |
|--------|--------------|-------------------|
| `validate_phase1.py` | — | pandas, numpy, pathlib |
| `phase_folder.py` | — | numpy/cupy, pandas, tqdm |
| `feature_extractor.py` | — | numpy/cupy, pandas, tqdm |
| `centroid_analyzer.py` | — | lightkurve, numpy, pandas, tqdm |
| `data_generator.py` | — | tensorflow, numpy, batman |
| `model.py` | — | tensorflow |
| `train_kepler.py` | `model.py` | tensorflow, sklearn, numpy, mlflow |
| `train_cnn_finetune.py` | `model.py`, `data_generator.py` | tensorflow, sklearn, numpy, mlflow |
| `train_xgboost.py` | — | xgboost, sklearn, numpy, pandas, mlflow, shap |
| `temperature_scaler.py` | — | numpy, scipy |
| `ensemble_predictor.py` | `temperature_scaler.py` | tensorflow, xgboost, numpy, pandas, tqdm |
| `evaluate.py` | `ensemble_predictor.py` | sklearn, matplotlib, shap, mlflow, numpy, pandas |
| `pipeline_integration.py` | `validate_phase1`, `phase_folder`, `feature_extractor`, `centroid_analyzer`, `ensemble_predictor` | — |

---

## Execution Order Constraints

```
PREP WEEK (before hackathon):
  1. train_kepler.py → kepler_pretrained.h5

HACKATHON (sequential critical path):
  2. validate_phase1.py           (gate — blocks all downstream)
  3. phase_folder.py              (blocks features + CNN inference)
  4. feature_extractor.py         ─┐
  5. centroid_analyzer.py         ─┤ (parallelizable)
  6. train_cnn_finetune.py        ─┘ (parallelizable with 4-5)
  7. train_xgboost.py             (after 4 completes)
  8. temperature_scaler.py        (after 6+7 complete)
  9. ensemble_predictor.py        (after 8)
  10. evaluate.py                 (after 9 — pass/fail gate for Phase 3)
```

---

## Key Schemas

### Phase-folded .npz (`data/folded/TIC_{id}_folded.npz`)

| Key | Shape | Dtype | Description |
|-----|-------|-------|-------------|
| `global` | (2001,) | float32 | Global view, normalized (median=0, min=-1) |
| `local` | (201,) | float32 | Local view, normalized (median=0, min=-1) |

### Feature Columns (appended to master.parquet)

| Column | Dtype | Source |
|--------|-------|--------|
| `odd_even_depth_diff` | float64 | feature_extractor |
| `secondary_eclipse_depth` | float64 | feature_extractor |
| `centroid_shift_sigma` | float64 | centroid_analyzer |
| `v_shape_metric` | float64 | feature_extractor |
| `crowdsap` | float64 | feature_extractor (from LC header) |
| `duration_period_ratio` | float64 | feature_extractor (computed) |
| `tls_sde` | float64 | Phase 1 (already exists) |
| `tls_snr` | float64 | Phase 1 (already exists) |

### Classification Columns (appended to master.parquet)

| Column | Dtype | Source |
|--------|-------|--------|
| `predicted_class` | int8 | ensemble_predictor |
| `confidence_pc` | float64 | ensemble_predictor |
| `prob_EB` | float64 | ensemble_predictor |
| `prob_Blend` | float64 | ensemble_predictor |
| `prob_StellarVar` | float64 | ensemble_predictor |
| `confidence_tier` | str | ensemble_predictor (Gold/Silver/Bronze) |
| `folded_path` | str | phase_folder |

---

## No Existing Analogs

Since no code exists in this repository yet, patterns are derived entirely from:
1. Phase 1 CONTEXT decisions (D-01 through D-15): modular steps, checkpoints, tqdm, JSON-lines, .npz+Parquet
2. Phase 2 RESEARCH section 8: module structure and execution dependency graph
3. AGENTS.md: stack pinning (TF 2.21, XGBoost 3.3, Python 3.12)
4. ADRs 0001–0004: architectural constraints on CNN architecture, augmentation, pre-training

When Phase 1 code is implemented, Phase 2 should mirror its:
- Directory structure conventions (`data/{stage}/sector{N}/`)
- CLI argument style (`argparse` with `--sectors`, `--step` flags)
- Checkpoint detection (check output file existence before processing)
- Logging format (JSON-lines with tic_id, step, status, elapsed_s)
- Error summary pattern (count failures, report at end, don't crash)

---

*Phase: 02-intelligence-feature-engineering-ml-classification*
*Pattern map generated: 2026-06-28*
