"""
ISRO BAH 2026 — Kepler DR24 CNN Pre-Training (Kaggle Notebook)
===============================================================

Purpose: Pre-train the Dual-View AstroNet CNN on Kepler DR24 labeled TCEs.
Output:  kepler_pretrained.h5 (base model for TESS fine-tuning per ADR-0004)

Kaggle Config:
    - Accelerator: GPU T4 x2
    - Internet: ON (for MAST downloads)
    - Persistence: ON (to save model artifact)

Architecture: 4-class dual-tower CNN (2001-global + 201-local phase-folded views)
    - Classes: Planet Candidate (0), Eclipsing Binary (1), Blend (2), Stellar Var (3)

Run this as a Kaggle notebook script or paste cells into a notebook.
"""

# %% [markdown]
# # ISRO BAH 2026 — Kepler DR24 CNN Pre-Training
#
# Pre-trains AstroNet dual-view CNN on ~34k Kepler DR24 labeled TCEs.
# Produces `kepler_pretrained.h5` for TESS fine-tuning.

# %% Install dependencies
import subprocess
subprocess.run(
    ['pip', 'install', '-q', 'lightkurve', 'astropy', 'astroquery',
     'wotan', 'transitleastsquares', 'scikit-learn', 'mlflow', 'tqdm'],
    check=True
)

# %% Imports
import os
import json
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, models, Input, callbacks, mixed_precision
from sklearn.model_selection import GroupShuffleSplit
from sklearn.utils.class_weight import compute_class_weight
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm.auto import tqdm
import requests
import lightkurve as lk
import mlflow

# Reproducibility
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

# %% Configuration
# Auto-detect environment
if os.path.exists('/kaggle/working'):
    BASE_DIR = Path('/kaggle/working')
else:
    BASE_DIR = Path('.')

DATA_DIR = BASE_DIR / 'data'
KEPLER_LC_DIR = DATA_DIR / 'kepler_lcs'
OUTPUT_DIR = DATA_DIR / 'kepler'
MODEL_DIR = DATA_DIR / 'models'

for d in [DATA_DIR, KEPLER_LC_DIR, OUTPUT_DIR, MODEL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Training hyperparameters
EPOCHS = 30
BATCH_SIZE = 64
LEARNING_RATE = 1e-3

# Set to None for full dataset, or a number like 500 for quick validation
LIMIT = None  # Change to 500 for a quick test run

print(f'TensorFlow: {tf.__version__}')
print(f'GPUs available: {tf.config.list_physical_devices("GPU")}')
print(f'Base directory: {BASE_DIR}')

# %% [markdown]
# ## Step 1: Download Kepler DR24 TCE Catalog

# %% Download TCE catalog
TCE_PATH = DATA_DIR / 'kepler_dr24_tce.csv'

if TCE_PATH.exists():
    print(f'Loading cached TCE catalog: {TCE_PATH}')
    tce_df = pd.read_csv(TCE_PATH)
else:
    print('Downloading Kepler DR24 TCE catalog from NASA Exoplanet Archive...')
    url = (
        'https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query='
        'select+kepid,tce_plnt_num,tce_period,tce_time0bk,tce_duration,'
        'tce_depth,av_training_set+from+q1_q17_dr24_tce&format=csv'
    )
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    with open(TCE_PATH, 'w') as f:
        f.write(response.text)
    tce_df = pd.read_csv(TCE_PATH)

print(f'TCE catalog: {len(tce_df)} entries')
print(f'Label distribution:\n{tce_df["av_training_set"].value_counts()}')

# %% Label mapping (4-class: PC=0, EB=1, Blend=2, StellarVar=3)
LABEL_MAPPING = {
    'PC': 0, 'KP': 0,           # Planet Candidate
    'EB': 1, 'AFP': 1,          # Eclipsing Binary
    'BEB': 2,                    # Background Blend
    'NTP': 3, 'V': 3, 'UNK': 3, 'IS': 3,  # Stellar Variability
}
CLASS_NAMES = ['PC', 'EB', 'Blend', 'StellarVar']


def map_label(av_training_set):
    """Map Kepler DR24 av_training_set to 4-class integer label."""
    if pd.isna(av_training_set) or av_training_set == '':
        return -1
    label_upper = str(av_training_set).strip().upper()
    if label_upper in LABEL_MAPPING:
        return LABEL_MAPPING[label_upper]
    if 'PLANET' in label_upper or label_upper == 'CP':
        return 0
    if 'BINARY' in label_upper or 'EB' in label_upper:
        return 1
    if 'BLEND' in label_upper or 'BEB' in label_upper:
        return 2
    return 3  # Default: stellar variability


# Apply labels
tce_df['label'] = tce_df['av_training_set'].apply(map_label)
tce_df = tce_df[tce_df['label'] >= 0].reset_index(drop=True)
print(f'\nAfter label filtering: {len(tce_df)} TCEs')
print(f'Class counts: { {CLASS_NAMES[i]: (tce_df["label"]==i).sum() for i in range(4)} }')

# %% [markdown]
# ## Step 2: Download Kepler Light Curves
#
# Downloads stitched long-cadence Kepler light curves via lightkurve.
# This is the slowest step (~2-4 hours for full dataset). Use LIMIT to test first.

# %% Download light curves
def download_single_kic(kic_id):
    """Download and save a single Kepler light curve."""
    dest_path = KEPLER_LC_DIR / f'{kic_id}_kepler.npz'
    if dest_path.exists():
        return 'EXISTS'
    try:
        search = lk.search_lightcurve(f'KIC {kic_id}', mission='Kepler', cadence='long')
        if len(search) == 0:
            return 'NOT_FOUND'
        lc_col = search.download_all()
        if lc_col is None or len(lc_col) == 0:
            return 'DOWNLOAD_FAILED'
        lc = lc_col.stitch()
        np.savez_compressed(
            str(dest_path),
            time=lc.time.value.astype(np.float64),
            flux=lc.flux.value.astype(np.float32),
            flux_err=lc.flux_err.value.astype(np.float32),
        )
        return 'SUCCESS'
    except Exception as e:
        return f'ERROR: {e}'


# Get unique KIC IDs to download
unique_kics = tce_df['kepid'].unique().tolist()
if LIMIT is not None:
    unique_kics = unique_kics[:LIMIT]

print(f'Downloading {len(unique_kics)} Kepler light curves...')
print('(Already downloaded files will be skipped)')

# Sequential download (Kaggle has limited parallelism for network I/O)
counts = {'SUCCESS': 0, 'EXISTS': 0, 'NOT_FOUND': 0, 'DOWNLOAD_FAILED': 0, 'ERROR': 0}
for i, kic in enumerate(tqdm(unique_kics, desc='Downloading LCs')):
    result = download_single_kic(kic)
    key = result if result in counts else 'ERROR'
    counts[key] += 1
    if (i + 1) % 50 == 0:
        print(f'  Progress: {i+1}/{len(unique_kics)} | {counts}')

print(f'\nDownload complete: {counts}')

# %% [markdown]
# ## Step 3: Phase-Fold Light Curves into CNN Input Format
#
# Produces 2001-point global view + 201-point local view per TCE.
# Normalization: median=0, min=-1 (AstroNet spec).

# %% Phase folding functions
def _safe_normalize(view):
    """Normalize: subtract median, scale so min=-1. Handles div-by-zero."""
    view = np.nan_to_num(view, nan=0.0)
    med = np.median(view)
    view = view - med
    min_val = np.min(view)
    if min_val < -1e-10:
        view = view / np.abs(min_val)
    return view.astype(np.float32)


def phase_fold_single(time, flux, period, t0, duration,
                      global_len=2001, local_len=201):
    """Phase-fold a light curve into global + local views."""
    phase = ((time - t0) % period) / period
    phase[phase > 0.5] -= 1.0

    # Global view: full orbit
    global_bins = np.linspace(-0.5, 0.5, global_len + 1)
    global_view = np.zeros(global_len, dtype=np.float32)
    for i in range(global_len):
        mask = (phase >= global_bins[i]) & (phase < global_bins[i + 1])
        if mask.sum() > 0:
            global_view[i] = np.nanmedian(flux[mask])

    # Local view: zoom around transit (±2x duration)
    half_width = min(2.0 * (duration / period), 0.25)
    local_bins = np.linspace(-half_width, half_width, local_len + 1)
    local_view = np.zeros(local_len, dtype=np.float32)
    for i in range(local_len):
        mask = (phase >= local_bins[i]) & (phase < local_bins[i + 1])
        if mask.sum() > 0:
            local_view[i] = np.nanmedian(flux[mask])

    return _safe_normalize(global_view), _safe_normalize(local_view)


# %% Process all TCEs
FOLDED_PATH = OUTPUT_DIR / 'kepler_dr24_folded.npz'

if FOLDED_PATH.exists():
    print(f'Loading pre-computed folded views from {FOLDED_PATH}')
    data = np.load(FOLDED_PATH)
    global_views = data['global_views']
    local_views = data['local_views']
    labels = data['labels']
    kic_ids = data['kic_ids']
else:
    # Filter to KICs with downloaded light curves
    available_kics = set()
    for f in KEPLER_LC_DIR.glob('*_kepler.npz'):
        try:
            available_kics.add(int(f.stem.split('_')[0]))
        except ValueError:
            pass

    df_available = tce_df[tce_df['kepid'].isin(available_kics)].reset_index(drop=True)
    print(f'TCEs with available light curves: {len(df_available)}')

    results = []
    for idx in tqdm(range(len(df_available)), desc='Phase-folding'):
        row = df_available.iloc[idx]
        kic_id = int(row['kepid'])
        lc_path = KEPLER_LC_DIR / f'{kic_id}_kepler.npz'

        try:
            with np.load(str(lc_path)) as lc_data:
                time = lc_data['time']
                flux = lc_data['flux']

            valid = np.isfinite(time) & np.isfinite(flux)
            time, flux = time[valid], flux[valid]
            if len(time) < 100:
                continue

            # Normalize flux to median=1
            med_flux = np.nanmedian(flux)
            if med_flux <= 0:
                continue
            flux = flux / med_flux

            period = float(row['tce_period'])
            t0 = float(row['tce_time0bk'])
            duration = float(row['tce_duration']) / 24.0  # hours -> days

            if period <= 0 or duration <= 0 or np.isnan(period) or np.isnan(t0):
                continue

            gv, lv = phase_fold_single(time, flux, period, t0, duration)
            results.append({
                'kic_id': kic_id,
                'global_view': gv,
                'local_view': lv,
                'label': int(row['label']),
            })
        except Exception:
            continue

    print(f'Successfully folded: {len(results)} TCEs')

    # Aggregate
    global_views = np.stack([r['global_view'] for r in results])
    local_views = np.stack([r['local_view'] for r in results])
    labels = np.array([r['label'] for r in results], dtype=np.int32)
    kic_ids = np.array([r['kic_id'] for r in results], dtype=np.int64)

    # Save checkpoint
    np.savez_compressed(
        str(FOLDED_PATH),
        global_views=global_views,
        local_views=local_views,
        labels=labels,
        kic_ids=kic_ids,
    )
    print(f'Saved folded views to {FOLDED_PATH}')

# Print stats
print(f'\nDataset shape: global={global_views.shape}, local={local_views.shape}')
print(f'Class distribution:')
for i, name in enumerate(CLASS_NAMES):
    count = (labels == i).sum()
    print(f'  {name}: {count} ({100*count/len(labels):.1f}%)')

# %% [markdown]
# ## Step 4: Build Dual-View AstroNet CNN
#
# Architecture per Shallue & Vanderburg 2018 adapted for 4-class output.
# - Global tower: 6 Conv1D layers (16→512 filters)
# - Local tower: 4 Conv1D layers (16→128 filters)
# - Merged: Dense(512) → Dense(256) → Dense(4, softmax)

# %% Model definition
def build_astronet_dual_view(global_len=2001, local_len=201, num_classes=4):
    """Build Dual-View AstroNet CNN for transit classification."""
    # Global View Tower (2001 points)
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

    # Local View Tower (201 points)
    local_input = Input(shape=(local_len, 1), name='local_view')
    l = layers.Conv1D(16, 5, activation='relu', padding='same')(local_input)
    l = layers.MaxPooling1D(5, strides=2)(l)
    l = layers.Conv1D(32, 5, activation='relu', padding='same')(l)
    l = layers.MaxPooling1D(5, strides=2)(l)
    l = layers.Conv1D(64, 5, activation='relu', padding='same')(l)
    l = layers.MaxPooling1D(5, strides=2)(l)
    l = layers.Conv1D(128, 5, activation='relu', padding='same')(l)
    l = layers.GlobalMaxPooling1D()(l)

    # Merge + Classification Head
    merged = layers.Concatenate()([g, l])
    x = layers.Dense(512, activation='relu')(merged)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    output = layers.Dense(num_classes, activation='softmax', dtype='float32',
                          name='class_probs')(x)

    return models.Model(inputs=[global_input, local_input], outputs=output,
                        name='astronet_dual_view')


# %% Data generator with augmentation
class KeplerDataGenerator(tf.keras.utils.Sequence):
    """Data generator with noise injection augmentation (50% probability)."""

    def __init__(self, global_views, local_views, labels,
                 batch_size=64, augment=False, shuffle=True):
        self.global_views = global_views
        self.local_views = local_views
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

        gv = self.global_views[batch_idx].reshape(-1, 2001, 1).astype(np.float32)
        lv = self.local_views[batch_idx].reshape(-1, 201, 1).astype(np.float32)
        y = self.labels[batch_idx]

        if self.augment:
            mask = np.random.random(len(gv)) < 0.5
            if mask.any():
                gv[mask] += np.random.normal(0, 0.01, gv[mask].shape).astype(np.float32)
                lv[mask] += np.random.normal(0, 0.01, lv[mask].shape).astype(np.float32)

        return [gv, lv], y

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)

# %% [markdown]
# ## Step 5: Train the Model
#
# - Per-KIC split (no data leakage from same star in train/val)
# - Mixed precision (float16) for T4 GPU efficiency
# - Noise augmentation during training
# - Class weights for imbalanced dataset

# %% Setup training
tf.keras.backend.clear_session()
mixed_precision.set_global_policy('mixed_float16')

# Per-KIC split to prevent data leakage (Bug #11 fix)
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
idx_train, idx_val = next(gss.split(global_views, labels, groups=kic_ids))

# Verify no overlap
train_kics = set(kic_ids[idx_train])
val_kics = set(kic_ids[idx_val])
assert len(train_kics & val_kics) == 0, 'Data leakage detected!'
print(f'Per-KIC split: {len(train_kics)} train KICs, {len(val_kics)} val KICs, 0 overlap')
print(f'Train samples: {len(idx_train)}, Val samples: {len(idx_val)}')

# Class weights
class_weights = compute_class_weight(
    'balanced', classes=np.unique(labels), y=labels[idx_train]
)
class_weight_dict = dict(enumerate(class_weights))
print(f'Class weights: {class_weight_dict}')

# Data generators
train_gen = KeplerDataGenerator(
    global_views[idx_train], local_views[idx_train], labels[idx_train],
    batch_size=BATCH_SIZE, augment=True, shuffle=True
)
val_gen = KeplerDataGenerator(
    global_views[idx_val], local_views[idx_val], labels[idx_val],
    batch_size=BATCH_SIZE, augment=False, shuffle=False
)

# Build and compile model
model = build_astronet_dual_view(num_classes=4)
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE),
    loss='sparse_categorical_crossentropy',
    metrics=['sparse_categorical_accuracy'],
)
model.summary()

# %% Train
MODEL_PATH = str(MODEL_DIR / 'kepler_pretrained.h5')

# MLflow tracking (local file-based)
mlflow.set_tracking_uri(f'file://{BASE_DIR}/.mlruns')
mlflow.set_experiment('kepler-pretrain')

with mlflow.start_run(run_name='kepler-pretrain-kaggle'):
    mlflow.log_params({
        'batch_size': BATCH_SIZE,
        'learning_rate': LEARNING_RATE,
        'epochs': EPOCHS,
        'optimizer': 'adam',
        'mixed_precision': 'float16',
        'train_size': len(idx_train),
        'val_size': len(idx_val),
        'seed': SEED,
        'per_kic_split': True,
        'augmentation': 'noise_injection_0.01',
    })

    history = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=EPOCHS,
        class_weight=class_weight_dict,
        callbacks=[
            callbacks.ModelCheckpoint(
                MODEL_PATH, save_best_only=True,
                monitor='val_loss', mode='min',
            ),
            callbacks.EarlyStopping(
                patience=7, restore_best_weights=True,
                monitor='val_loss',
            ),
            callbacks.ReduceLROnPlateau(
                factor=0.5, patience=3, monitor='val_loss',
            ),
        ],
    )

    # Log metrics
    for epoch in range(len(history.history['val_loss'])):
        mlflow.log_metrics({
            'val_loss': history.history['val_loss'][epoch],
            'val_acc': history.history['val_sparse_categorical_accuracy'][epoch],
            'train_loss': history.history['loss'][epoch],
        }, step=epoch)

    best_val_loss = min(history.history['val_loss'])
    best_val_acc = max(history.history['val_sparse_categorical_accuracy'])
    mlflow.log_metrics({'best_val_loss': best_val_loss, 'best_val_acc': best_val_acc})
    mlflow.log_artifact(MODEL_PATH)

print(f'\n{"="*60}')
print(f'✓ Kepler pre-training complete!')
print(f'  Best val_loss: {best_val_loss:.4f}')
print(f'  Best val_acc:  {best_val_acc:.4f}')
print(f'  Model saved:   {MODEL_PATH}')
print(f'{"="*60}')

# %% [markdown]
# ## Step 6: Quick Evaluation

# %% Evaluate on validation set
from sklearn.metrics import classification_report, confusion_matrix

# Get predictions
val_gv = global_views[idx_val].reshape(-1, 2001, 1).astype(np.float32)
val_lv = local_views[idx_val].reshape(-1, 201, 1).astype(np.float32)
val_labels = labels[idx_val]

# Load best model
best_model = tf.keras.models.load_model(MODEL_PATH, compile=False)
preds = best_model.predict([val_gv, val_lv], batch_size=128)
pred_classes = np.argmax(preds, axis=1)

print('\nClassification Report:')
print(classification_report(val_labels, pred_classes, target_names=CLASS_NAMES))

print('\nConfusion Matrix:')
cm = confusion_matrix(val_labels, pred_classes)
print(cm)

# %% [markdown]
# ## Step 7: Save Artifacts for TESS Fine-Tuning
#
# Copy the model to Kaggle output directory so it persists after the session.

# %% Save final artifacts
import shutil

# Copy to /kaggle/working for download
output_model_path = BASE_DIR / 'kepler_pretrained.h5'
shutil.copy2(MODEL_PATH, output_model_path)

# Also save the folded data as a reusable artifact
output_data_path = BASE_DIR / 'kepler_dr24_folded.npz'
shutil.copy2(str(FOLDED_PATH), output_data_path)

print(f'\n✓ Artifacts saved to Kaggle output:')
print(f'  Model: {output_model_path} ({output_model_path.stat().st_size / 1e6:.1f} MB)')
print(f'  Data:  {output_data_path} ({output_data_path.stat().st_size / 1e6:.1f} MB)')
print(f'\nThese files will be available as a Kaggle Dataset for the TESS fine-tuning notebook.')

# %% [markdown]
# ## Next Steps
#
# 1. Save this notebook's output as a **Kaggle Dataset** (e.g., `isro-kepler-pretrained`)
# 2. Create a new notebook for TESS fine-tuning that imports this dataset
# 3. The fine-tuning notebook loads `kepler_pretrained.h5` and trains on ExoFOP-TESS labels
#
# **Expected results:** val_acc > 0.92 on 4-class Kepler classification
