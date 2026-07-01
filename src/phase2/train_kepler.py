"""Kepler DR24 CNN pre-training — runs during prep week only, NOT during hackathon.

Produces: data/models/kepler_pretrained.h5
Dataset: data/kepler/kepler_dr24_folded.npz (pre-prepared by kepler_data_prep.py)

Bug fixes addressed:
    - Bug #11: Per-KIC split to prevent data leakage (same star in train/val)
    - Bug #12: Add basic augmentation (noise injection) during pre-training
    - Bug #15: Pin MLflow tracking URI to project root

Usage:
    python src/phase2/train_kepler.py --epochs 30 --batch-size 64 --lr 1e-3
"""

import os
import argparse
import subprocess
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras import callbacks, mixed_precision
from sklearn.model_selection import GroupShuffleSplit
from sklearn.utils.class_weight import compute_class_weight
import mlflow

from src.phase2.model import build_astronet_dual_view

# Reproducibility
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

# Bug #15 Fix: Pin MLflow tracking URI to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
MLFLOW_TRACKING_URI = f'file://{PROJECT_ROOT}/.mlruns'


def get_git_hash() -> str:
    """Return short git commit hash for MLflow run naming."""
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD']
        ).decode().strip()[:7]
    except Exception:
        return 'unknown'


class KeplerDataGenerator(tf.keras.utils.Sequence):
    """Data generator with basic augmentation for Kepler pre-training.
    
    Bug #12 Fix: Add noise injection augmentation to reduce discontinuity
    between pre-training (clean) and fine-tuning (7x augmented).
    
    Augmentation (applied with 50% probability):
        - Gaussian noise injection (sigma = 0.01)
    """
    
    def __init__(self, global_views, local_views, labels, 
                 batch_size=64, augment=False, shuffle=True, **kwargs):
        super().__init__(**kwargs)  # Required by Keras 3
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
            gv, lv = self._apply_augmentation(gv, lv)
        
        return (gv, lv), y  # Keras 3 requires tuple, not list
    
    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)
    
    def _apply_augmentation(self, gv, lv):
        """Apply basic noise augmentation with 50% probability per sample."""
        mask = np.random.random(len(gv)) < 0.5
        if mask.any():
            noise_sigma = 0.01
            gv[mask] += np.random.normal(0, noise_sigma, gv[mask].shape).astype(np.float32)
            lv[mask] += np.random.normal(0, noise_sigma, lv[mask].shape).astype(np.float32)
        return gv, lv


def main(args):
    # GPU setup
    tf.keras.backend.clear_session()
    mixed_precision.set_global_policy('mixed_float16')

    # Load pre-prepared Kepler phase-folded views
    data_path = 'data/kepler/kepler_dr24_folded.npz'
    if not os.path.exists(data_path):
        raise FileNotFoundError(
            f'{data_path} not found. Run kepler_data_prep.py first.\n'
            f'This script must be run during the prep week, not during the hackathon.'
        )

    data = np.load(data_path)
    global_views = data['global_views']  # (N, 2001)
    local_views = data['local_views']    # (N, 201)
    labels = data['labels']              # (N,) int 0-3
    
    # Bug #11 Fix: Load KIC IDs for per-star split to prevent data leakage
    if 'kic_ids' in data:
        kic_ids = data['kic_ids']
        print(f'Using per-KIC split to prevent data leakage')
    else:
        print('Warning: kic_ids not found in data, falling back to sample-based split')
        kic_ids = None

    print(f'Loaded Kepler DR24: {len(labels)} TCEs, '
          f'classes: {np.bincount(labels)}')

    # Bug #11 Fix: Per-KIC stratified split to prevent same star in train/val
    if kic_ids is not None:
        # Use GroupShuffleSplit to ensure no KIC appears in both train and val
        gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
        idx_train, idx_val = next(gss.split(global_views, labels, groups=kic_ids))
        
        # Verify no KIC overlap
        train_kics = set(kic_ids[idx_train])
        val_kics = set(kic_ids[idx_val])
        overlap = train_kics & val_kics
        if overlap:
            raise ValueError(f'Data leak: {len(overlap)} KICs in both train and val!')
        print(f'Per-KIC split: {len(train_kics)} train KICs, {len(val_kics)} val KICs, 0 overlap')
    else:
        # Fallback to sample-based split (Bug #20 risk if same star has multiple TCEs)
        from sklearn.model_selection import train_test_split
        idx_train, idx_val = train_test_split(
            np.arange(len(labels)), test_size=0.2,
            stratify=labels, random_state=SEED,
        )

    # Class weights for imbalanced dataset
    class_weights = compute_class_weight(
        'balanced', classes=np.unique(labels), y=labels[idx_train]
    )
    class_weight_dict = dict(enumerate(class_weights))

    # Bug #12 Fix: Use data generator with augmentation
    train_gen = KeplerDataGenerator(
        global_views[idx_train], local_views[idx_train], labels[idx_train],
        batch_size=args.batch_size, augment=True, shuffle=True
    )
    val_gen = KeplerDataGenerator(
        global_views[idx_val], local_views[idx_val], labels[idx_val],
        batch_size=args.batch_size, augment=False, shuffle=False
    )

    # Build model
    model = build_astronet_dual_view(num_classes=4)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=args.lr),
        loss='sparse_categorical_crossentropy',
        metrics=['sparse_categorical_accuracy'],
    )
    model.summary()

    # Output directory
    os.makedirs('data/models', exist_ok=True)
    model_path = 'data/models/kepler_pretrained.h5'

    # Bug #15 Fix: Use pinned MLflow tracking URI
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment('kepler-pretrain')

    with mlflow.start_run(run_name=f'kepler-pretrain-{get_git_hash()}'):
        mlflow.set_tag('git_commit', get_git_hash())
        mlflow.set_tag('phase', '2-intelligence')
        mlflow.set_tag('dataset', 'kepler-dr24')
        mlflow.log_params({
            'batch_size': args.batch_size,
            'learning_rate': args.lr,
            'epochs': args.epochs,
            'optimizer': 'adam',
            'mixed_precision': 'float16',
            'train_size': len(idx_train),
            'val_size': len(idx_val),
            'seed': SEED,
            'per_kic_split': kic_ids is not None,  # Bug #11
            'augmentation': 'noise_injection',  # Bug #12
        })

        # Train with generators
        history = model.fit(
            train_gen,
            validation_data=val_gen,
            epochs=args.epochs,
            class_weight=class_weight_dict,
            callbacks=[
                callbacks.ModelCheckpoint(
                    model_path, save_best_only=True,
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

        # Log per-epoch metrics
        for epoch in range(len(history.history['val_loss'])):
            mlflow.log_metrics({
                'val_loss': history.history['val_loss'][epoch],
                'val_acc': history.history['val_sparse_categorical_accuracy'][epoch],
                'train_loss': history.history['loss'][epoch],
            }, step=epoch)

        # Log final model artifact
        mlflow.log_artifact(model_path)
        best_val_loss = min(history.history['val_loss'])
        best_val_acc = max(history.history['val_sparse_categorical_accuracy'])
        mlflow.log_metrics({
            'best_val_loss': best_val_loss,
            'best_val_acc': best_val_acc,
        })

    print(f'✓ Kepler pre-training complete. Best val_loss={best_val_loss:.4f}, '
          f'val_acc={best_val_acc:.4f}')
    print(f'  Model saved to: {model_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Pre-train AstroNet CNN on Kepler DR24 (prep week only)'
    )
    parser.add_argument('--epochs', type=int, default=30)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--lr', type=float, default=1e-3)
    args = parser.parse_args()
    main(args)
