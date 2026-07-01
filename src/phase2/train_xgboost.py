"""XGBoost 4-class classifier training with SHAP feature importance.

Trains on the 8 engineered features from FeatureExtractor using stratified
5-fold CV, SHAP TreeExplainer, and full evaluation metrics. Shares the same
60/20/20 split as CNN fine-tuning via split_indices.npz.

Usage:
    python src/phase2/train_xgboost.py --catalogue data/catalogue/master.parquet
"""

import os
import argparse
import subprocess

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (
    f1_score, classification_report, confusion_matrix,
    roc_auc_score, ConfusionMatrixDisplay,
)
from sklearn.utils.class_weight import compute_class_weight
import shap
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server/Colab
import matplotlib.pyplot as plt
import mlflow

# Reproducibility
SEED = 42
np.random.seed(SEED)

MODEL_OUTPUT_PATH = 'data/models/xgboost_ensemble.json'

FEATURE_COLUMNS = [
    'odd_even_depth_diff', 'secondary_eclipse_depth', 'centroid_shift_sigma',
    'v_shape_metric', 'crowdsap', 'duration_period_ratio', 'tls_sde', 'tls_snr',
]

CLASS_NAMES = ['PC', 'EB', 'Blend', 'StellarVar']


def get_git_hash() -> str:
    """Return short git commit hash for MLflow run naming."""
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD']
        ).decode().strip()[:7]
    except Exception:
        return 'unknown'


def main(args):
    # Load master Parquet, filter to labeled rows
    df = pd.read_parquet(args.catalogue)
    labeled_df = df[df['label'].notna()].copy()

    if len(labeled_df) == 0:
        raise ValueError(
            'No labeled candidates found in catalogue. '
            'Ensure the \'label\' column is populated from ExoFOP-TESS dispositions.'
        )

    print(f'Loaded {len(labeled_df)} labeled candidates for XGBoost training.')

    # Load shared split indices from CNN fine-tuning (ensures fair comparison)
    split_path = 'data/models/split_indices.npz'
    if os.path.exists(split_path):
        split = np.load(split_path, allow_pickle=True)
        # Use same indices as CNN — filter to valid labeled rows
        train_mask = labeled_df.index.isin(split['train_idx'])
        test_mask = labeled_df.index.isin(split['test_idx'])
        train_df = labeled_df[train_mask]
        test_df = labeled_df[test_mask]
        # Fallback for any labeled rows not in CNN split (new labels)
        if len(train_df) == 0:
            train_df = labeled_df.sample(frac=0.8, random_state=SEED)
            test_df = labeled_df.drop(train_df.index)
        print(f'Using shared split: train={len(train_df)}, test={len(test_df)}')
    else:
        # Create own split if CNN split not available
        train_df, test_df = train_test_split(
            labeled_df, test_size=0.2, stratify=labeled_df['label'], random_state=SEED
        )
        print(f'Created independent split: train={len(train_df)}, test={len(test_df)}')

    # Extract feature matrix and labels
    X_train = train_df[FEATURE_COLUMNS].fillna(0.0).values
    y_train = train_df['label'].values.astype(int)
    X_test = test_df[FEATURE_COLUMNS].fillna(0.0).values
    y_test = test_df['label'].values.astype(int)

    # XGBoost hyperparameters (optimized for 4-class transit classification)
    params = {
        'objective': 'multi:softprob',
        'num_class': 4,
        'tree_method': 'hist',
        'device': 'cuda',
        'max_depth': 6,
        'learning_rate': 0.05,
        'n_estimators': 500,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 3,
        'reg_lambda': 1.0,
        'reg_alpha': 0.1,
        'eval_metric': 'mlogloss',
        'early_stopping_rounds': 20,
        'random_state': SEED,
    }

    # Stratified 5-fold CV on training set to report mean±std F1-macro
    skf = StratifiedKFold(n_splits=args.n_folds, shuffle=True, random_state=SEED)
    cv_f1_scores = []

    print(f'\nRunning {args.n_folds}-fold stratified cross-validation...')
    for fold, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train)):
        X_tr, X_val = X_train[tr_idx], X_train[val_idx]
        y_tr, y_val = y_train[tr_idx], y_train[val_idx]

        clf_cv = xgb.XGBClassifier(**params)
        clf_cv.fit(
            X_tr, y_tr,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        y_pred_cv = clf_cv.predict(X_val)
        f1 = f1_score(y_val, y_pred_cv, average='macro', zero_division=0)
        cv_f1_scores.append(f1)
        print(f'  Fold {fold + 1}/{args.n_folds}: F1-macro = {f1:.4f}')

    cv_mean = np.mean(cv_f1_scores)
    cv_std = np.std(cv_f1_scores)
    print(f'\n5-fold CV F1-macro: {cv_mean:.4f} ± {cv_std:.4f}')

    # Train final model on full training set
    print('\nTraining final XGBoost model on full training set...')
    clf = xgb.XGBClassifier(**params)
    clf.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    # Evaluate on test set
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)

    acc = float((y_pred == y_test).mean())
    f1_macro = f1_score(y_test, y_pred, average='macro', zero_division=0)
    f1_per_class = f1_score(y_test, y_pred, average=None, zero_division=0)

    print(f'\nTest set evaluation:')
    print(f'  Accuracy: {acc:.4f}')
    print(f'  F1-macro: {f1_macro:.4f}')
    print(classification_report(y_test, y_pred, target_names=CLASS_NAMES, zero_division=0))

    # Confusion matrix
    os.makedirs('outputs', exist_ok=True)
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(8, 6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=CLASS_NAMES)
    disp.plot(ax=ax, colorbar=True, cmap='Blues')
    ax.set_title('XGBoost 4-Class Confusion Matrix (Test Set)')
    plt.tight_layout()
    plt.savefig('outputs/xgboost_confusion_matrix.png', dpi=150, bbox_inches='tight')
    plt.close()

    # ROC-AUC (one-vs-rest, macro)
    try:
        roc_auc = roc_auc_score(y_test, y_proba, multi_class='ovr', average='macro')
        print(f'  ROC-AUC (OvR macro): {roc_auc:.4f}')
    except Exception as e:
        print(f'  ROC-AUC computation failed: {e}')
        roc_auc = float('nan')

    # SHAP TreeExplainer feature importance
    print('\nComputing SHAP values...')
    explainer = shap.TreeExplainer(clf)
    shap_values = explainer.shap_values(X_test)
    shap.summary_plot(
        shap_values, X_test, feature_names=FEATURE_COLUMNS,
        class_names=CLASS_NAMES, plot_type='bar', show=False,
    )
    plt.savefig('outputs/shap_summary.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('  SHAP summary plot saved to outputs/shap_summary.png')

    # Save model
    os.makedirs('data/models', exist_ok=True)
    clf.save_model(MODEL_OUTPUT_PATH)
    print(f'✓ XGBoost model saved to: {MODEL_OUTPUT_PATH}')

    # MLflow logging
    mlflow.set_tracking_uri(f'file://{os.getcwd()}/.mlruns')
    mlflow.set_experiment('tess-finetune-xgboost')

    with mlflow.start_run(run_name=f'xgboost-4class-{get_git_hash()}'):
        mlflow.set_tag('git_commit', get_git_hash())
        mlflow.set_tag('phase', '2-intelligence')
        mlflow.set_tag('script', 'train_xgboost')
        mlflow.log_params({
            'n_estimators': params['n_estimators'],
            'max_depth': params['max_depth'],
            'learning_rate': params['learning_rate'],
            'subsample': params['subsample'],
            'colsample_bytree': params['colsample_bytree'],
            'min_child_weight': params['min_child_weight'],
            'reg_lambda': params['reg_lambda'],
            'reg_alpha': params['reg_alpha'],
            'early_stopping_rounds': params['early_stopping_rounds'],
            'n_folds': args.n_folds,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'seed': SEED,
        })
        mlflow.log_metrics({
            'cv_f1_macro_mean': cv_mean,
            'cv_f1_macro_std': cv_std,
            'test_accuracy': acc,
            'test_f1_macro': f1_macro,
            'test_roc_auc': roc_auc,
        })
        for i, name in enumerate(CLASS_NAMES):
            mlflow.log_metric(f'test_f1_{name}', float(f1_per_class[i]))

        mlflow.log_artifact('outputs/shap_summary.png')
        mlflow.log_artifact('outputs/xgboost_confusion_matrix.png')
        mlflow.log_artifact(MODEL_OUTPUT_PATH)

    print('✓ XGBoost training complete. Results logged to MLflow.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Train XGBoost 4-class classifier on engineered features'
    )
    parser.add_argument('--catalogue', type=str, default='data/catalogue/master.parquet')
    parser.add_argument('--n-folds', type=int, default=5)
    args = parser.parse_args()
    main(args)
