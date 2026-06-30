"""Kepler DR24 CNN pre-training — runs during prep week only, NOT during hackathon.

Produces: data/models/kepler_pretrained.h5
Dataset: data/kepler/kepler_dr24_folded.npz (pre-prepared by kepler_data_prep.py)

Usage:
    python src/phase2/train_kepler.py --epochs 30 --batch-size 64 --lr 1e-3
"""

import os
import argparse
import subprocess

import numpy as np
import tensorflow as tf
from tensorflow.keras import callbacks, mixed_precision
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
import mlflow

from src.phase2.model import build_astronet_dual_view

# Reproducibility
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)


def get_git_hash() -> str:
    """Return short git commit hash for MLflow run naming."""
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD']
        ).decode().strip()[:7]
    except Exception:
        return 'unknown'


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

    print(f'Loaded Kepler DR24: {len(labels)} TCEs, '
          f'classes: {np.bincount(labels)}')

    # Stratified train/val split (80/20)
    idx_train, idx_val = train_test_split(
        np.arange(len(labels)), test_size=0.2,
        stratify=labels, random_state=SEED,
    )

    # Class weights for imbalanced dataset
    class_weights = compute_class_weight(
        'balanced', classes=np.unique(labels), y=labels[idx_train]
    )
    class_weight_dict = dict(enumerate(class_weights))

    # Reshape for CNN input: (N, length, 1)
    gv_train = global_views[idx_train].reshape(-1, 2001, 1)
    lv_train = local_views[idx_train].reshape(-1, 201, 1)
    gv_val = global_views[idx_val].reshape(-1, 2001, 1)
    lv_val = local_views[idx_val].reshape(-1, 201, 1)

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

    # MLflow tracking
    mlflow.set_tracking_uri(f'file://{os.getcwd()}/.mlruns')
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
        })

        # Train
        history = model.fit(
            [gv_train, lv_train], labels[idx_train],
            validation_data=([gv_val, lv_val], labels[idx_val]),
            batch_size=args.batch_size,
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
