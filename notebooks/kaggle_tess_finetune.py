"""
ISRO BAH 2026 — TESS Fine-Tuning + XGBoost + Ensemble (Kaggle Notebook)
========================================================================

Purpose: Fine-tune the Kepler-pretrained CNN on TESS ExoFOP-labeled TOIs,
         train XGBoost on engineered features, and calibrate the ensemble.

Inputs (from Kaggle Dataset):
    - kepler_pretrained.h5 (from Notebook #1 output)

Outputs:
    - cnn_finetuned.h5
    - xgboost_ensemble.json
    - temperature_scalar.npz
    - master_catalogue.parquet (with predictions)

Kaggle Config:
    - Accelerator: GPU T4 x1
    - Internet: ON (for MAST/ExoFOP downloads)
    - Persistence: ON
    - Add Notebook #1 output as Input Dataset

Strategy: Download ONLY known TOIs from ExoFOP (already labeled),
          skip full TLS search (saves ~10+ hours).
"""

# %% [markdown]
# # ISRO BAH 2026 — TESS Fine-Tuning + Ensemble
#
# Fine-tunes Kepler-pretrained CNN on ExoFOP-TESS labeled TOIs.
# Trains XGBoost on engineered features. Calibrates ensemble.

# %% Install dependencies
import subprocess
subprocess.run(
    ['pip', 'install', '-q', 'lightkurve', 'astropy', 'astroquery',
     'wotan', 'scikit-learn', 'mlflow', 'tqdm', 'xgboost', 'shap'],
    check=True
)

# %% Imports
import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, models, Input, callbacks, mixed_precision
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from pathlib import Path
from tqdm.auto import tqdm
import requests
import lightkurve as lk
import xgboost as xgb
import mlflow

# Reproducibility
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

# %% Configuration
if os.path.exists('/kaggle/working'):
    BASE_DIR = Path('/kaggle/working')
else:
    BASE_DIR = Path('.')

DATA_DIR = BASE_DIR / 'data'
TESS_LC_DIR = DATA_DIR / 'tess_lcs'
FOLDED_DIR = DATA_DIR / 'tess_folded'
MODEL_DIR = DATA_DIR / 'models'

for d in [DATA_DIR, TESS_LC_DIR, FOLDED_DIR, MODEL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- IMPORTANT: Set this to your Notebook #1 output path ---
# On Kaggle, add your Kepler pretrain output as an Input Dataset.
# It will appear at /kaggle/input/<dataset-name>/
KEPLER_MODEL_PATH = None
# Auto-detect common locations
for candidate in [
    Path('/kaggle/input/isro-kepler-pretrained/kepler_pretrained.h5'),
    Path('/kaggle/input/kepler-pretrained/kepler_pretrained.h5'),
    BASE_DIR / 'kepler_pretrained.h5',
    Path('kaggle_output/kepler_pretrained.h5'),
]:
    if candidate.exists():
        KEPLER_MODEL_PATH = str(candidate)
        break

if KEPLER_MODEL_PATH is None:
    print("⚠ WARNING: kepler_pretrained.h5 not found!")
    print("  Add your Notebook #1 output as a Kaggle Input Dataset,")
    print("  or place kepler_pretrained.h5 in the working directory.")
    print("  Will train from scratch if not found.")
else:
    print(f'✓ Found Kepler model: {KEPLER_MODEL_PATH}')

# Hyperparameters
EPOCHS = 50
BATCH_SIZE = 32
LEARNING_RATE = 1e-4
LIMIT = 300  # Number of TOIs to download (None for all ~6000)

CLASS_NAMES = ['PC', 'EB', 'Blend', 'StellarVar']

print(f'TensorFlow: {tf.__version__}')
print(f'GPUs: {tf.config.list_physical_devices("GPU")}')

# %% [markdown]
# ## Step 1: Download ExoFOP-TESS TOI Catalog (with labels)
#
# ExoFOP provides dispositions (CP, FP, KP, PC, FA, etc.) for each TOI.
# We download only labeled TOIs — these are our training data.

# %% Download ExoFOP TOI catalog
EXOFOP_PATH = DATA_DIR / 'exofop_toi.csv'

if EXOFOP_PATH.exists():
    print(f'Loading cached ExoFOP catalog: {EXOFOP_PATH}')
    toi_df = pd.read_csv(EXOFOP_PATH)
else:
    print('Downloading ExoFOP-TESS TOI catalog...')
    # ExoFOP bulk CSV download
    url = 'https://exofop.ipac.caltech.edu/tess/download_toi.php?sort=toi&output=csv'
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    with open(EXOFOP_PATH, 'w') as f:
        f.write(response.text)
    toi_df = pd.read_csv(EXOFOP_PATH)

print(f'ExoFOP TOI catalog: {len(toi_df)} entries')
print(f'Columns: {list(toi_df.columns[:15])}...')

# %% Map ExoFOP dispositions to 4-class labels
# TFOPWG Disposition column: CP, KP, PC, FP, FA, EB, IS, V, etc.
TESS_LABEL_MAP = {
    'CP': 0, 'KP': 0, 'PC': 0,        # Planet Candidate / Confirmed
    'EB': 1, 'SB': 1,                   # Eclipsing Binary / Spectroscopic Binary
    'BEB': 2, 'BTP': 2, 'NEB': 2,      # Background EB / Nearby EB (Blends)
    'FP': 1, 'FA': 3,                   # False Positive (mostly EB), False Alarm (stellar)
    'IS': 3, 'V': 3,                    # Instrumental / Variable (stellar variability)
}


def map_tess_label(disposition):
    """Map TFOPWG disposition to 4-class label."""
    if pd.isna(disposition) or str(disposition).strip() == '':
        return -1
    disp = str(disposition).strip().upper()
    if disp in TESS_LABEL_MAP:
        return TESS_LABEL_MAP[disp]
    if 'PLANET' in disp:
        return 0
    if 'EB' in disp or 'BINARY' in disp:
        return 1
    return -1  # Unknown — exclude


# Find disposition column (ExoFOP has varied column names)
disp_col = None
for col in ['TFOPWG Disposition', 'tfopwg_disp', 'Disposition', 'disposition']:
    if col in toi_df.columns:
        disp_col = col
        break

if disp_col is None:
    # Try case-insensitive match
    for col in toi_df.columns:
        if 'disp' in col.lower():
            disp_col = col
            break

print(f'Using disposition column: {disp_col}')
toi_df['label'] = toi_df[disp_col].apply(map_tess_label)

# Filter to labeled only
labeled_df = toi_df[toi_df['label'] >= 0].reset_index(drop=True)
print(f'Labeled TOIs: {len(labeled_df)}')
print(f'Class distribution: { {CLASS_NAMES[i]: (labeled_df["label"]==i).sum() for i in range(4)} }')

# Find TIC ID and period columns
tic_col = None
for col in ['TIC ID', 'TIC', 'tic_id', 'tid']:
    if col in labeled_df.columns:
        tic_col = col
        break
    for c in labeled_df.columns:
        if 'tic' in c.lower():
            tic_col = c
            break
    if tic_col:
        break

period_col = None
for col in ['Period (days)', 'Period', 'period', 'pl_orbper']:
    if col in labeled_df.columns:
        period_col = col
        break
    for c in labeled_df.columns:
        if 'period' in c.lower() or 'per' in c.lower():
            period_col = c
            break
    if period_col:
        break

duration_col = None
for col in ['Duration (hours)', 'Duration', 'duration', 'pl_trandur']:
    if col in labeled_df.columns:
        duration_col = col
        break
    for c in labeled_df.columns:
        if 'dur' in c.lower():
            duration_col = c
            break
    if duration_col:
        break

epoch_col = None
for col in ['Epoch (BJD)', 'Epoch', 'epoch', 'pl_tranmid']:
    if col in labeled_df.columns:
        epoch_col = col
        break
    for c in labeled_df.columns:
        if 'epoch' in c.lower() or 'tranmid' in c.lower() or 't0' in c.lower():
            epoch_col = c
            break
    if epoch_col:
        break

depth_col = None
for col in ['Depth (ppm)', 'Depth', 'depth', 'tran_depth']:
    if col in labeled_df.columns:
        depth_col = col
        break
    for c in labeled_df.columns:
        if 'depth' in c.lower():
            depth_col = c
            break
    if depth_col:
        break

print(f'TIC column: {tic_col}')
print(f'Period column: {period_col}')
print(f'Duration column: {duration_col}')
print(f'Epoch column: {epoch_col}')
print(f'Depth column: {depth_col}')

# Apply limit
if LIMIT is not None:
    labeled_df = labeled_df.head(LIMIT)
    print(f'\nLimited to {len(labeled_df)} TOIs for training')

# %% [markdown]
# ## Step 2: Download TESS Light Curves for Labeled TOIs
#
# We only download light curves for TOIs that have labels — much faster
# than downloading all 20k+ targets per sector.

# %% Download TESS light curves
def download_tess_lc(tic_id):
    """Download TESS PDCSAP light curve for a TIC ID."""
    dest_path = TESS_LC_DIR / f'tic{tic_id}_tess.npz'
    if dest_path.exists():
        return 'EXISTS'
    try:
        search = lk.search_lightcurve(
            f'TIC {tic_id}', mission='TESS', author='SPOC', cadence='short'
        )
        if len(search) == 0:
            # Fallback to 2-min cadence
            search = lk.search_lightcurve(f'TIC {tic_id}', mission='TESS', author='SPOC')
        if len(search) == 0:
            return 'NOT_FOUND'

        # Download first available sector
        lc = search[0].download()
        if lc is None:
            return 'DOWNLOAD_FAILED'

        # Use PDCSAP flux
        time = lc.time.value.astype(np.float64)
        flux = lc.flux.value.astype(np.float32)
        flux_err = lc.flux_err.value.astype(np.float32)

        # Basic quality: remove NaN
        valid = np.isfinite(time) & np.isfinite(flux) & np.isfinite(flux_err)
        time, flux, flux_err = time[valid], flux[valid], flux_err[valid]

        if len(time) < 100:
            return 'TOO_SHORT'

        np.savez_compressed(
            str(dest_path),
            time=time, flux=flux, flux_err=flux_err,
        )
        return 'SUCCESS'
    except Exception as e:
        return f'ERROR'


tic_ids = labeled_df[tic_col].astype(int).unique().tolist()
print(f'Downloading TESS LCs for {len(tic_ids)} unique TIC IDs...')

counts = {'SUCCESS': 0, 'EXISTS': 0, 'NOT_FOUND': 0, 'DOWNLOAD_FAILED': 0, 'TOO_SHORT': 0, 'ERROR': 0}
for i, tic in enumerate(tqdm(tic_ids, desc='Downloading TESS LCs')):
    result = download_tess_lc(tic)
    key = result if result in counts else 'ERROR'
    counts[key] += 1

print(f'\nDownload results: {counts}')
print(f'Total available: {counts["SUCCESS"] + counts["EXISTS"]}')

# %% [markdown]
# ## Step 3: Preprocess and Phase-Fold TESS Light Curves

# %% Phase folding (same logic as Kepler notebook)
def _safe_normalize(view):
    """Normalize: subtract median, scale so min=-1."""
    view = np.nan_to_num(view, nan=0.0)
    med = np.median(view)
    view = view - med
    min_val = np.min(view)
    if min_val < -1e-10:
        view = view / np.abs(min_val)
    return view.astype(np.float32)


def phase_fold_tess(time, flux, period, t0, duration_hours):
    """Phase-fold TESS light curve into global (2001) + local (201) views."""
    duration = duration_hours / 24.0  # hours to days

    # Simple detrending: normalize to median=1
    med = np.nanmedian(flux)
    if med <= 0:
        return None, None
    flux_norm = flux / med

    # Sigma clip (remove 5-sigma outliers)
    std = np.nanstd(flux_norm)
    good = np.abs(flux_norm - 1.0) < 5 * std
    time, flux_norm = time[good], flux_norm[good]

    if len(time) < 50:
        return None, None

    # Phase fold
    phase = ((time - t0) % period) / period
    phase[phase > 0.5] -= 1.0

    # Global view
    global_bins = np.linspace(-0.5, 0.5, 2002)
    global_view = np.zeros(2001, dtype=np.float32)
    for i in range(2001):
        mask = (phase >= global_bins[i]) & (phase < global_bins[i + 1])
        if mask.sum() > 0:
            global_view[i] = np.nanmedian(flux_norm[mask])

    # Local view
    half_width = min(2.0 * (duration / period), 0.25)
    if half_width < 0.005:
        half_width = 0.05
    local_bins = np.linspace(-half_width, half_width, 202)
    local_view = np.zeros(201, dtype=np.float32)
    for i in range(201):
        mask = (phase >= local_bins[i]) & (phase < local_bins[i + 1])
        if mask.sum() > 0:
            local_view[i] = np.nanmedian(flux_norm[mask])

    return _safe_normalize(global_view), _safe_normalize(local_view)


# %% Process all labeled TOIs
print('Phase-folding TESS light curves...')
results = []

for idx in tqdm(range(len(labeled_df)), desc='Phase-folding'):
    row = labeled_df.iloc[idx]
    tic_id = int(row[tic_col])
    lc_path = TESS_LC_DIR / f'tic{tic_id}_tess.npz'

    if not lc_path.exists():
        continue

    try:
        period = float(row[period_col])
        t0 = float(row[epoch_col])
        duration = float(row[duration_col]) if duration_col else 2.0  # default 2 hours

        if period <= 0 or np.isnan(period) or np.isnan(t0):
            continue
        if np.isnan(duration) or duration <= 0:
            duration = 2.0

        with np.load(str(lc_path)) as data:
            time = data['time']
            flux = data['flux']
            flux_err = data['flux_err']

        gv, lv = phase_fold_tess(time, flux, period, t0, duration)
        if gv is None:
            continue

        # Compute basic features for XGBoost
        depth = float(row[depth_col]) if depth_col and not pd.isna(row.get(depth_col)) else 0.0
        median_flux_err = float(np.median(flux_err)) if len(flux_err) > 0 else 0.001

        results.append({
            'tic_id': tic_id,
            'global_view': gv,
            'local_view': lv,
            'label': int(row['label']),
            'period': period,
            'duration': duration,
            'depth_ppm': depth,
            'median_flux_err': median_flux_err,
        })
    except Exception:
        continue

print(f'\nSuccessfully processed: {len(results)} TOIs')
print(f'Class distribution:')
labels_arr = np.array([r['label'] for r in results])
for i, name in enumerate(CLASS_NAMES):
    print(f'  {name}: {(labels_arr == i).sum()}')

# Save checkpoint
global_views = np.stack([r['global_view'] for r in results])
local_views = np.stack([r['local_view'] for r in results])
labels = np.array([r['label'] for r in results], dtype=np.int32)
tic_ids_arr = np.array([r['tic_id'] for r in results], dtype=np.int64)

# %% [markdown]
# ## Step 4: Fine-Tune CNN on TESS Data
#
# Load kepler_pretrained.h5, freeze early layers, fine-tune on TESS labels.

# %% Build or load model
def build_astronet_dual_view(global_len=2001, local_len=201, num_classes=4):
    """Build Dual-View AstroNet CNN (same as Kepler notebook)."""
    global_input = Input(shape=(global_len, 1), name='global_view')
    g = layers.Conv1D(16, 5, activation='relu', padding='same')(global_input)
    g = layers.MaxPooling1D(5, strides=2)(g)
    g = layers.Conv1D(32, 5, activation='relu', padding='same')(g)
    g = layers.MaxPooling1D(5, strides=2)(g)
    g = layers.Conv1D(64, 5, activation='relu', padding='same')(g)
    g = layers.MaxPooling1D(5, strides=2)(g)
    g = layers.Conv1D(128, 5, activation='relu', padding='same')(g)
    g = layers.MaxPooling1D(5, strides=2)(g)
    g = layers.Conv1D(256, 5, activation='relu', padding='same')(g)
    g = layers.MaxPooling1D(5, strides=2)(g)
    g = layers.Conv1D(512, 5, activation='relu', padding='same')(g)
    g = layers.GlobalMaxPooling1D()(g)

    local_input = Input(shape=(local_len, 1), name='local_view')
    l = layers.Conv1D(16, 5, activation='relu', padding='same')(local_input)
    l = layers.MaxPooling1D(5, strides=2)(l)
    l = layers.Conv1D(32, 5, activation='relu', padding='same')(l)
    l = layers.MaxPooling1D(5, strides=2)(l)
    l = layers.Conv1D(64, 5, activation='relu', padding='same')(l)
    l = layers.MaxPooling1D(5, strides=2)(l)
    l = layers.Conv1D(128, 5, activation='relu', padding='same')(l)
    l = layers.GlobalMaxPooling1D()(l)

    merged = layers.Concatenate()([g, l])
    x = layers.Dense(512, activation='relu')(merged)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    output = layers.Dense(num_classes, activation='softmax', dtype='float32',
                          name='class_probs')(x)
    return models.Model(inputs=[global_input, local_input], outputs=output,
                        name='astronet_dual_view')


# %% Load pre-trained model and setup fine-tuning
tf.keras.backend.clear_session()
mixed_precision.set_global_policy('mixed_float16')

if KEPLER_MODEL_PATH and os.path.exists(KEPLER_MODEL_PATH):
    print(f'Loading Kepler pre-trained model from {KEPLER_MODEL_PATH}')
    model = tf.keras.models.load_model(KEPLER_MODEL_PATH, compile=False)
    # Freeze first 12 layers (early conv feature detectors)
    for layer in model.layers[:12]:
        layer.trainable = False
    frozen_info = '12 layers frozen (transfer learning)'
else:
    print('No pre-trained model found — training from scratch')
    model = build_astronet_dual_view(num_classes=4)
    frozen_info = 'none (training from scratch)'

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE),
    loss='sparse_categorical_crossentropy',
    metrics=['sparse_categorical_accuracy'],
)
print(f'Model ready. Frozen: {frozen_info}')
print(f'Trainable params: {model.count_params():,}')

# %% Train/val/test split (60/20/20, per-TIC to prevent leakage)
from sklearn.model_selection import GroupShuffleSplit

# First split: 80% train+cal, 20% test
gss1 = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
idx_trainval, idx_test = next(gss1.split(global_views, labels, groups=tic_ids_arr))

# Second split: 75% train, 25% cal (of the 80% = 60/20 overall)
gss2 = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED)
idx_train, idx_cal = next(gss2.split(
    global_views[idx_trainval], labels[idx_trainval],
    groups=tic_ids_arr[idx_trainval]
))
# Map back to original indices
idx_train = idx_trainval[idx_train]
idx_cal = idx_trainval[idx_cal]

print(f'Split: train={len(idx_train)}, cal={len(idx_cal)}, test={len(idx_test)}')

# Verify no TIC overlap
assert len(set(tic_ids_arr[idx_train]) & set(tic_ids_arr[idx_cal])) == 0
assert len(set(tic_ids_arr[idx_train]) & set(tic_ids_arr[idx_test])) == 0
print('✓ No TIC overlap between splits')

# Class weights
present_classes = np.unique(labels[idx_train])
computed_weights = compute_class_weight('balanced', classes=present_classes, y=labels[idx_train])
class_weight_dict = {i: 1.0 for i in range(4)}
for cls, w in zip(present_classes, computed_weights):
    class_weight_dict[int(cls)] = float(w)
print(f'Class weights: {class_weight_dict}')

# %% Data generator with 7x augmentation
class TessDataGenerator(tf.keras.utils.Sequence):
    """7x augmentation generator for TESS fine-tuning."""

    def __init__(self, global_views, local_views, labels,
                 batch_size=32, augment=False, shuffle=True, **kwargs):
        super().__init__(**kwargs)
        self.gv = global_views
        self.lv = local_views
        self.labels = labels
        self.batch_size = batch_size
        self.augment = augment
        self.shuffle = shuffle
        self.indices = np.arange(len(labels))
        self.on_epoch_end()

    def __len__(self):
        return int(np.ceil(len(self.labels) / self.batch_size))

    def __getitem__(self, idx):
        start = idx * self.batch_size
        end = min(start + self.batch_size, len(self.labels))
        batch_idx = self.indices[start:end]

        gv = self.gv[batch_idx].reshape(-1, 2001, 1).astype(np.float32)
        lv = self.lv[batch_idx].reshape(-1, 201, 1).astype(np.float32)
        y = self.labels[batch_idx]

        if self.augment:
            gv, lv = self._augment(gv, lv)

        return (gv, lv), y  # Tuple for Keras 3

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)

    def _augment(self, gv, lv):
        """Apply random augmentation (1 of 7 strategies per sample)."""
        for i in range(len(gv)):
            choice = np.random.randint(0, 7)
            if choice == 0:
                pass  # Original
            elif choice == 1:
                # Noise injection
                gv[i] += np.random.normal(0, 0.01, gv[i].shape).astype(np.float32)
                lv[i] += np.random.normal(0, 0.01, lv[i].shape).astype(np.float32)
            elif choice == 2:
                # Time shift (edge-padded)
                shift = np.random.randint(-5, 6)
                if shift != 0:
                    gv[i] = self._shift(gv[i], shift)
                    lv[i] = self._shift(lv[i], shift)
            else:
                # Choices 3-6: Synthetic depth variation (±10% of depth)
                scale = np.random.uniform(0.9, 1.1)
                med_g = np.median(gv[i])
                med_l = np.median(lv[i])
                gv[i] = med_g + (gv[i] - med_g) * scale
                lv[i] = med_l + (lv[i] - med_l) * scale
        return gv, lv

    @staticmethod
    def _shift(view, shift):
        """Shift with edge padding (no wrapping)."""
        result = np.zeros_like(view)
        if shift > 0:
            result[shift:] = view[:-shift]
            result[:shift] = view[0]
        else:
            result[:shift] = view[-shift:]
            result[shift:] = view[-1]
        return result


# %% Train CNN
train_gen = TessDataGenerator(
    global_views[idx_train], local_views[idx_train], labels[idx_train],
    batch_size=BATCH_SIZE, augment=True, shuffle=True
)
val_gen = TessDataGenerator(
    global_views[idx_cal], local_views[idx_cal], labels[idx_cal],
    batch_size=BATCH_SIZE, augment=False, shuffle=False
)

CNN_MODEL_PATH = str(MODEL_DIR / 'cnn_finetuned.h5')

MLFLOW_DB = BASE_DIR / 'mlflow.db'
mlflow.set_tracking_uri(f'sqlite:///{MLFLOW_DB}')
mlflow.set_experiment('tess-finetune')

with mlflow.start_run(run_name='cnn-finetune-tess'):
    mlflow.log_params({
        'batch_size': BATCH_SIZE, 'lr': LEARNING_RATE, 'epochs': EPOCHS,
        'frozen_layers': frozen_info, 'train_size': len(idx_train),
        'augmentation': '7x (noise, shift, depth_scale)',
    })

    history = model.fit(
        train_gen, validation_data=val_gen,
        epochs=EPOCHS,
        class_weight=class_weight_dict,
        callbacks=[
            callbacks.ModelCheckpoint(CNN_MODEL_PATH, save_best_only=True,
                                     monitor='val_sparse_categorical_accuracy', mode='max'),
            callbacks.EarlyStopping(patience=10, restore_best_weights=True,
                                   monitor='val_sparse_categorical_accuracy', mode='max'),
            callbacks.ReduceLROnPlateau(factor=0.5, patience=5,
                                       monitor='val_sparse_categorical_accuracy', mode='max'),
        ],
    )

    best_val_acc = max(history.history['val_sparse_categorical_accuracy'])
    mlflow.log_metric('best_val_acc', best_val_acc)

print(f'\n✓ CNN fine-tuning complete. Best val_acc: {best_val_acc:.4f}')
print(f'  Model saved: {CNN_MODEL_PATH}')

# %% [markdown]
# ## Step 5: Train XGBoost on Engineered Features

# %% Compute features for XGBoost
def compute_features(gv, lv, period, duration, depth_ppm, median_flux_err):
    """Compute 8 engineered features for a single candidate."""
    # 1. Odd/even depth difference (simplified — use phase-folded view)
    n = len(gv)
    mid = n // 2
    transit_width = max(5, int(n * 0.02))
    left_transit = gv[mid - transit_width:mid]
    right_transit = gv[mid:mid + transit_width]
    odd_depth = 1.0 - np.median(left_transit) if len(left_transit) > 0 else 0
    even_depth = 1.0 - np.median(right_transit) if len(right_transit) > 0 else 0
    combined_err = max(np.std(gv) / np.sqrt(max(transit_width, 1)), 1e-10)
    odd_even_diff = abs(odd_depth - even_depth) / combined_err

    # 2. Secondary eclipse depth (at phase 0.5 = edges of global view)
    edge_w = max(1, n // 20)
    sec_region = np.concatenate([gv[:edge_w], gv[-edge_w:]])
    oot_region = gv[n // 4:int(n * 0.45)]
    sec_depth = max(float(np.median(oot_region) - np.median(sec_region)), 0.0)

    # 3. V-shape metric
    lv_flat = lv.flatten()
    depth = 1.0 - np.min(lv_flat)
    if depth > 1e-5:
        flat_threshold = np.min(lv_flat) + 0.1 * depth
        flat_dur = np.sum(lv_flat < flat_threshold)
        below_half = lv_flat < (1.0 - depth / 2.0)
        total_dur = max(np.sum(below_half), 1)
        v_shape = 1.0 - (flat_dur / total_dur)
    else:
        v_shape = 0.0

    # 4. Duration/period ratio
    dur_period = (duration / 24.0) / period if period > 0 else 0.0

    # 5. Depth as SNR proxy
    snr = (depth_ppm * 1e-6) / max(median_flux_err, 1e-10)

    return {
        'odd_even_depth_diff': float(odd_even_diff),
        'secondary_eclipse_depth': float(sec_depth),
        'v_shape_metric': float(np.clip(v_shape, 0, 1)),
        'duration_period_ratio': float(dur_period),
        'depth_snr': float(snr),
        'transit_depth': float(depth),
        'median_flux_err': float(median_flux_err),
        'period': float(period),
    }


# Build feature matrix
print('Computing engineered features...')
feature_records = []
for r in tqdm(results, desc='Features'):
    feats = compute_features(
        r['global_view'], r['local_view'],
        r['period'], r['duration'],
        r['depth_ppm'], r['median_flux_err']
    )
    feature_records.append(feats)

feature_df = pd.DataFrame(feature_records)
FEATURE_COLS = list(feature_df.columns)
print(f'Feature matrix: {feature_df.shape}')
print(feature_df.describe())

# %% Train XGBoost
X_train = feature_df.iloc[idx_train].values
X_cal = feature_df.iloc[idx_cal].values
X_test = feature_df.iloc[idx_test].values
y_train = labels[idx_train]
y_cal = labels[idx_cal]
y_test = labels[idx_test]

# Handle class imbalance via sample weights
sample_weights = np.array([class_weight_dict[int(l)] for l in y_train])

# XGBoost requires contiguous class labels [0, 1, 2, ...].
# With small LIMIT, some classes may be missing (e.g. no Blend samples),
# so we remap to contiguous labels and keep a mapping to restore them.
unique_train_classes = np.sort(np.unique(y_train))
n_xgb_classes = len(unique_train_classes)
label_to_xgb = {int(c): i for i, c in enumerate(unique_train_classes)}
xgb_to_label = {i: int(c) for i, c in enumerate(unique_train_classes)}

y_train_xgb = np.array([label_to_xgb[int(l)] for l in y_train])
y_cal_xgb = np.array([label_to_xgb.get(int(l), 0) for l in y_cal])

xgb_model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    objective='multi:softprob',
    num_class=n_xgb_classes,
    eval_metric='mlogloss',
    use_label_encoder=False,
    random_state=SEED,
    tree_method='hist',
)

xgb_model.fit(
    X_train, y_train_xgb,
    sample_weight=sample_weights,
    eval_set=[(X_cal, y_cal_xgb)],
    verbose=20,
)

XGB_MODEL_PATH = str(MODEL_DIR / 'xgboost_ensemble.json')
xgb_model.save_model(XGB_MODEL_PATH)
print(f'\n✓ XGBoost trained. Model saved: {XGB_MODEL_PATH}')
print(f'  Classes in training: {unique_train_classes} (mapped to 0..{n_xgb_classes-1})')

# %% [markdown]
# ## Step 6: Ensemble + Temperature Calibration

# %% Ensemble predictions on calibration set
# CNN predictions (always 4-class output)
best_cnn = tf.keras.models.load_model(CNN_MODEL_PATH, compile=False)
cal_gv = global_views[idx_cal].reshape(-1, 2001, 1).astype(np.float32)
cal_lv = local_views[idx_cal].reshape(-1, 201, 1).astype(np.float32)
cnn_probs_cal = best_cnn.predict((cal_gv, cal_lv), batch_size=64)

# XGBoost predictions — remap from n_xgb_classes back to 4-class
xgb_raw_probs_cal = xgb_model.predict_proba(X_cal)
# Expand to full 4-class probability matrix
xgb_probs_cal = np.zeros((len(X_cal), 4), dtype=np.float32)
for xgb_idx, orig_class in xgb_to_label.items():
    xgb_probs_cal[:, orig_class] = xgb_raw_probs_cal[:, xgb_idx]

# Weighted ensemble: 0.6*CNN + 0.4*XGBoost
ALPHA_CNN = 0.6
ALPHA_XGB = 0.4
ensemble_probs_cal = ALPHA_CNN * cnn_probs_cal + ALPHA_XGB * xgb_probs_cal

# %% Temperature scaling (Platt calibration)
from scipy.optimize import minimize_scalar


def compute_ece(probs, labels, n_bins=10):
    """Expected Calibration Error."""
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    correct = (predictions == labels).astype(float)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        if mask.sum() > 0:
            avg_conf = confidences[mask].mean()
            avg_acc = correct[mask].mean()
            ece += mask.sum() * abs(avg_conf - avg_acc)
    return ece / len(labels)


def temperature_scale(logits, T):
    """Apply temperature scaling to logits."""
    scaled = logits / T
    exp_scaled = np.exp(scaled - np.max(scaled, axis=1, keepdims=True))
    return exp_scaled / exp_scaled.sum(axis=1, keepdims=True)


# Convert probs to logits for scaling
ensemble_logits_cal = np.log(np.clip(ensemble_probs_cal, 1e-10, 1.0))


def ece_at_temperature(T):
    """ECE as function of temperature (for optimization)."""
    scaled_probs = temperature_scale(ensemble_logits_cal, T)
    return compute_ece(scaled_probs, y_cal)


# Find optimal temperature
result = minimize_scalar(ece_at_temperature, bounds=(0.1, 10.0), method='bounded')
optimal_T = result.x
ece_before = compute_ece(ensemble_probs_cal, y_cal)
ece_after = ece_at_temperature(optimal_T)

print(f'\nTemperature Calibration:')
print(f'  Optimal T: {optimal_T:.3f}')
print(f'  ECE before: {ece_before:.4f}')
print(f'  ECE after:  {ece_after:.4f}')
print(f'  Target:     < 0.04 {"✓" if ece_after < 0.04 else "✗"}')

# Save temperature
TEMP_PATH = str(MODEL_DIR / 'temperature_scalar.npz')
np.savez(TEMP_PATH, temperature=np.float32(optimal_T),
         alpha_cnn=np.float32(ALPHA_CNN), alpha_xgb=np.float32(ALPHA_XGB))
print(f'  Saved: {TEMP_PATH}')

# %% [markdown]
# ## Step 7: Final Evaluation on Test Set

# %% Test set evaluation
# CNN on test
test_gv = global_views[idx_test].reshape(-1, 2001, 1).astype(np.float32)
test_lv = local_views[idx_test].reshape(-1, 201, 1).astype(np.float32)
cnn_probs_test = best_cnn.predict((test_gv, test_lv), batch_size=64)

# XGBoost on test — remap to 4-class
xgb_raw_probs_test = xgb_model.predict_proba(X_test)
xgb_probs_test = np.zeros((len(X_test), 4), dtype=np.float32)
for xgb_idx, orig_class in xgb_to_label.items():
    xgb_probs_test[:, orig_class] = xgb_raw_probs_test[:, xgb_idx]

# Ensemble + calibration
ensemble_logits_test = np.log(np.clip(
    ALPHA_CNN * cnn_probs_test + ALPHA_XGB * xgb_probs_test, 1e-10, 1.0
))
calibrated_probs = temperature_scale(ensemble_logits_test, optimal_T)
ensemble_preds = np.argmax(calibrated_probs, axis=1)

print('\n' + '=' * 60)
print('FINAL TEST SET RESULTS (Calibrated Ensemble)')
print('=' * 60)
print(classification_report(
    y_test, ensemble_preds,
    labels=list(range(4)),
    target_names=CLASS_NAMES,
    zero_division=0,
))
print(f'Confusion Matrix:')
print(confusion_matrix(y_test, ensemble_preds, labels=list(range(4))))

test_ece = compute_ece(calibrated_probs, y_test)
print(f'\nTest ECE: {test_ece:.4f} (target < 0.04)')

# %% [markdown]
# ## Step 8: Save All Artifacts

# %% Save outputs
import shutil

# Copy models to /kaggle/working for persistence
for src, name in [
    (CNN_MODEL_PATH, 'cnn_finetuned.h5'),
    (XGB_MODEL_PATH, 'xgboost_ensemble.json'),
    (TEMP_PATH, 'temperature_scalar.npz'),
]:
    dest = BASE_DIR / name
    shutil.copy2(src, dest)
    print(f'✓ {name} ({dest.stat().st_size / 1e6:.2f} MB)')

# Save split indices for reproducibility
np.savez(
    str(BASE_DIR / 'split_indices.npz'),
    train_idx=idx_train, cal_idx=idx_cal, test_idx=idx_test,
)
print(f'✓ split_indices.npz')

# Save feature importance
if hasattr(xgb_model, 'feature_importances_'):
    importance = dict(zip(FEATURE_COLS, xgb_model.feature_importances_))
    print(f'\nXGBoost Feature Importance:')
    for feat, imp in sorted(importance.items(), key=lambda x: -x[1]):
        print(f'  {feat}: {imp:.4f}')

print(f'\n{"="*60}')
print(f'✓ ALL DONE — Pipeline complete!')
print(f'  CNN val_acc:  {best_val_acc:.4f}')
print(f'  Test ECE:     {test_ece:.4f}')
print(f'  Temperature:  {optimal_T:.3f}')
print(f'{"="*60}')
