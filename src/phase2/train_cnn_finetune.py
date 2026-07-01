"""TESS fine-tuning of AstroNet CNN — runs during hackathon after Kepler pre-training.

Loads data/models/kepler_pretrained.h5, freezes early conv layers, and fine-tunes
on ExoFOP-TESS labeled candidates with 7x augmentation. Saves cnn_finetuned.h5.

Bug fixes addressed:
    - Bug #14: Auto-call PhaseFolder if folded_path column is missing
    - Bug #15: Pin MLflow tracking URI to project root

Usage:
    python src/phase2/train_cnn_finetune.py --epochs 50 --batch-size 32 --lr 1e-4
"""

import os
import argparse
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import callbacks, mixed_precision
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
import mlflow

from src.phase2.data_generator import TransitDataGenerator

# Reproducibility
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

MODEL_INPUT_PATH = 'data/models/kepler_pretrained.h5'
MODEL_OUTPUT_PATH = 'data/models/cnn_finetuned.h5'

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


def ensure_phase_folded(df: pd.DataFrame, catalogue_path: str) -> pd.DataFrame:
    """Bug #14 Fix: Ensure all candidates have phase-folded views.
    
    If folded_path column is missing or has nulls, run PhaseFolder to generate
    the required global/local views for CNN training.
    
    Args:
        df: DataFrame with candidates (must have tls_period, tls_t0, tls_duration).
        catalogue_path: Path to the master catalogue parquet.
        
    Returns:
        DataFrame with folded_path column populated.
    """
    # Check if folded_path column exists and has valid paths
    needs_folding = False
    
    if 'folded_path' not in df.columns:
        needs_folding = True
        print('folded_path column missing from catalogue - running PhaseFolder...')
    else:
        # Check for missing or invalid paths
        missing_count = df['folded_path'].isna().sum()
        if missing_count > 0:
            print(f'{missing_count} candidates missing folded_path - running PhaseFolder...')
            needs_folding = True
        else:
            # Verify paths exist
            invalid_count = sum(1 for p in df['folded_path'] if not Path(str(p)).exists())
            if invalid_count > 0:
                print(f'{invalid_count} folded_path entries point to missing files - running PhaseFolder...')
                needs_folding = True
    
    if needs_folding:
        from src.phase2.phase_folder import PhaseFolder
        
        # Infer directories from catalogue path
        catalogue_dir = Path(catalogue_path).parent
        preprocessed_dir = str(catalogue_dir.parent / 'preprocessed')
        folded_dir = str(catalogue_dir.parent / 'folded')
        
        # Try alternate paths if standard paths don't exist
        if not Path(preprocessed_dir).exists():
            preprocessed_dir = 'outputs/preprocessed'
        if not Path(folded_dir).exists():
            Path(folded_dir).mkdir(parents=True, exist_ok=True)
        
        print(f'Running PhaseFolder: preprocessed_dir={preprocessed_dir}, folded_dir={folded_dir}')
        
        folder = PhaseFolder(
            catalogue_path=catalogue_path,
            preprocessed_dir=preprocessed_dir,
            folded_dir=folded_dir
        )
        folder.run_all()
        
        # Reload catalogue with updated folded_path
        df = pd.read_parquet(catalogue_path)
    
    return df


def main(args):
    # GPU setup
    tf.keras.backend.clear_session()
    mixed_precision.set_global_policy('mixed_float16')

    # Load Kepler pre-trained model
    if not os.path.exists(MODEL_INPUT_PATH):
        raise FileNotFoundError(
            f'{MODEL_INPUT_PATH} not found. Run train_kepler.py during prep week first.\n'
            f'Kepler pre-training is a prerequisite (ADR-0004).'
        )

    base_model = tf.keras.models.load_model(MODEL_INPUT_PATH, compile=False)

    # Freeze first 12 layers (3 Conv+Pool pairs per tower × 2 towers)
    # These are early feature detectors (edges, gradients) learned on Kepler
    for layer in base_model.layers[:12]:
        layer.trainable = False

    # Compile with lower learning rate for fine-tuning
    base_model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=args.lr),
        loss='sparse_categorical_crossentropy',
        metrics=['sparse_categorical_accuracy'],
    )

    # Load master Parquet, filter to ExoFOP-labeled candidates
    df = pd.read_parquet(args.catalogue)
    
    # Bug #14 Fix: Ensure all candidates have phase-folded views
    df = ensure_phase_folded(df, args.catalogue)
    
    labeled_df = df[df['label'].notna()].copy()

    if len(labeled_df) == 0:
        raise ValueError(
            'No labeled candidates found in catalogue. '
            'Ensure the \'label\' column is populated from ExoFOP-TESS dispositions.'
        )

    print(f'Loaded {len(labeled_df)} labeled candidates for fine-tuning.')
    print(f'Class distribution: {labeled_df["label"].value_counts().to_dict()}')

    # 3-way stratified split: 60% train, 20% calibration, 20% test (D-12)
    train_df, temp_df = train_test_split(
        labeled_df, test_size=0.4, stratify=labeled_df['label'], random_state=SEED
    )
    cal_df, test_df = train_test_split(
        temp_df, test_size=0.5, stratify=temp_df['label'], random_state=SEED
    )

    # Verify split integrity: no TIC ID overlap between splits (data leak prevention)
    train_tics = set(train_df['tic_id'].values)
    cal_tics = set(cal_df['tic_id'].values)
    test_tics = set(test_df['tic_id'].values)
    assert len(train_tics & cal_tics) == 0, 'TIC ID overlap between train and calibration sets!'
    assert len(train_tics & test_tics) == 0, 'TIC ID overlap between train and test sets!'
    assert len(cal_tics & test_tics) == 0, 'TIC ID overlap between calibration and test sets!'

    print(f'Split: train={len(train_df)}, calibration={len(cal_df)}, test={len(test_df)}')

    # Data generators — augmentation for train only (D-04)
    train_gen = TransitDataGenerator(train_df, batch_size=args.batch_size, augment=True)
    val_gen = TransitDataGenerator(cal_df, batch_size=args.batch_size, augment=False)

    # Class weights for imbalanced dataset
    class_weights = compute_class_weight(
        'balanced', classes=np.unique(train_df['label'].values.astype(int)),
        y=train_df['label'].values.astype(int)
    )
    class_weight_dict = dict(enumerate(class_weights))

    # Output directory
    os.makedirs('data/models', exist_ok=True)

    # Save split indices for XGBoost and ensemble (shared split for fair comparison)
    np.savez(
        'data/models/split_indices.npz',
        train_idx=train_df.index.values,
        cal_idx=cal_df.index.values,
        test_idx=test_df.index.values,
    )

    # Bug #15 Fix: Use pinned MLflow tracking URI
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment('tess-finetune-xgboost')

    with mlflow.start_run(run_name=f'cnn-finetune-{get_git_hash()}'):
        mlflow.set_tag('git_commit', get_git_hash())
        mlflow.set_tag('phase', '2-intelligence')
        mlflow.set_tag('script', 'train_cnn_finetune')
        mlflow.log_params({
            'batch_size': args.batch_size,
            'learning_rate': args.lr,
            'epochs': args.epochs,
            'optimizer': 'adam',
            'mixed_precision': 'float16',
            'frozen_layers': 12,
            'train_size': len(train_df),
            'cal_size': len(cal_df),
            'test_size': len(test_df),
            'seed': SEED,
            'base_model': MODEL_INPUT_PATH,
        })

        # Train with fine-tuning
        history = base_model.fit(
            train_gen,
            validation_data=val_gen,
            epochs=args.epochs,
            class_weight=class_weight_dict,
            callbacks=[
                callbacks.ModelCheckpoint(
                    MODEL_OUTPUT_PATH, save_best_only=True,
                    monitor='val_sparse_categorical_accuracy', mode='max',
                ),
                callbacks.EarlyStopping(
                    patience=10, restore_best_weights=True,
                    monitor='val_sparse_categorical_accuracy', mode='max',
                ),
                callbacks.ReduceLROnPlateau(
                    factor=0.5, patience=5, monitor='val_sparse_categorical_accuracy',
                    mode='max',
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
        mlflow.log_artifact(MODEL_OUTPUT_PATH)
        mlflow.log_artifact('data/models/split_indices.npz')
        best_val_acc = max(history.history['val_sparse_categorical_accuracy'])
        mlflow.log_metric('best_val_acc', best_val_acc)

    print(f'✓ CNN fine-tuning complete. Best val_acc={best_val_acc:.4f}')
    print(f'  Model saved to: {MODEL_OUTPUT_PATH}')
    print(f'  Split indices saved to: data/models/split_indices.npz')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Fine-tune AstroNet CNN on TESS ExoFOP labels (hackathon phase)'
    )
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--lr', type=float, default=1e-4)
    parser.add_argument('--catalogue', type=str, default='data/catalogue/master.parquet')
    args = parser.parse_args()
    main(args)
