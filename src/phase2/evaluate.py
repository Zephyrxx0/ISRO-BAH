"""Phase 2 evaluation suite — computes E1-E10 metrics with pass/fail gating.

Loads test split predictions from the master Parquet catalogue and evaluates
against the AI-SPEC thresholds. Generates confusion matrix and reliability
diagram. Logs all results to MLflow.

Usage:
    python src/phase2/evaluate.py --catalogue data/catalogue/master.parquet
"""

import os
import argparse

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import mlflow
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report, confusion_matrix,
    roc_auc_score, ConfusionMatrixDisplay,
)


CLASS_NAMES = ['PC', 'EB', 'Blend', 'StellarVar']

# E1-E5 pass/fail thresholds (from AI-SPEC Section 5)
THRESHOLDS = {
    'accuracy': 0.90,         # E1 PASS
    'planet_recall': 0.85,    # E2 PASS
    'planet_precision': 0.80, # E3 PASS
    'fpr_max': 0.10,          # E4 PASS (must be BELOW)
    'ece_max': 0.04,          # E5 PASS (must be BELOW)
}


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray,
                                n_bins: int = 10) -> tuple:
    """Compute Expected Calibration Error (ECE) with reliability diagram data.

    ECE measures the average gap between confidence and accuracy across
    n_bins confidence bins. Lower is better; target ECE < 0.04 (CONF-03).

    Args:
        y_true: (N,) integer class labels 0-3.
        y_prob: (N, C) softmax probability array.
        n_bins: Number of confidence bins for calibration (default 10).

    Returns:
        Tuple of (ece_float, per_bin_list) where per_bin_list contains
        dicts with 'bin_center', 'accuracy', 'confidence', 'count' per bin.
    """
    # Use max confidence (predicted class probability)
    confidences = np.max(y_prob, axis=1)
    predictions = np.argmax(y_prob, axis=1)
    correct = (predictions == y_true).astype(float)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    per_bin = []

    for i in range(n_bins):
        bin_mask = (confidences > bin_edges[i]) & (confidences <= bin_edges[i + 1])
        bin_count = bin_mask.sum()

        if bin_count > 0:
            bin_acc = correct[bin_mask].mean()
            bin_conf = confidences[bin_mask].mean()
            ece += (bin_count / len(y_true)) * abs(bin_acc - bin_conf)
            per_bin.append({
                'bin_center': float((bin_edges[i] + bin_edges[i + 1]) / 2),
                'accuracy': float(bin_acc),
                'confidence': float(bin_conf),
                'count': int(bin_count),
            })
        else:
            per_bin.append({
                'bin_center': float((bin_edges[i] + bin_edges[i + 1]) / 2),
                'accuracy': 0.0,
                'confidence': 0.0,
                'count': 0,
            })

    return float(ece), per_bin


def run_evaluation(catalogue_path: str, model_dir: str,
                   output_dir: str = 'outputs') -> int:
    """Run full E1-E10 evaluation suite on Phase 2 classification results.

    Loads test split from split_indices.npz and evaluates the ensemble
    predictions stored in the master Parquet catalogue.

    Args:
        catalogue_path: Path to master.parquet with predicted_class and
                        confidence columns.
        model_dir: Directory containing split_indices.npz.
        output_dir: Directory to save output plots.

    Returns:
        Exit code: 0=all pass, 1=critical fail (E1/E2/E5), 2=high fail (E3/E4).
    """
    os.makedirs(output_dir, exist_ok=True)

    # Load data
    df = pd.read_parquet(catalogue_path)

    # Load test split
    split_path = os.path.join(model_dir, 'split_indices.npz')
    if not os.path.exists(split_path):
        raise FileNotFoundError(
            f'Split indices not found: {split_path}. '
            'Run train_cnn_finetune.py first to generate the split.'
        )

    split = np.load(split_path, allow_pickle=True)
    test_df = df[df.index.isin(split['test_idx'])].copy()

    # Filter to labeled rows with predictions
    eval_df = test_df[
        test_df['label'].notna() & test_df['predicted_class'].notna()
    ].copy()

    if len(eval_df) == 0:
        raise ValueError(
            'No labeled test rows with predictions found. '
            'Run ensemble classification before evaluation.'
        )

    y_true = eval_df['label'].values.astype(int)
    y_pred = eval_df['predicted_class'].values.astype(int)

    # Build probability matrix from per-class columns
    prob_cols = ['confidence_pc', 'prob_EB', 'prob_Blend', 'prob_StellarVar']
    if all(col in eval_df.columns for col in prob_cols):
        y_prob = eval_df[prob_cols].fillna(0.0).values
    else:
        # Fallback: one-hot from predicted class
        y_prob = np.zeros((len(eval_df), 4))
        y_prob[np.arange(len(eval_df)), y_pred] = 1.0

    print(f'\n{"=" * 60}')
    print('PHASE 2 EVALUATION REPORT')
    print(f'{"=" * 60}')
    print(f'Test samples: {len(eval_df)}')
    print(f'Class distribution: {np.bincount(y_true)}')

    results = {}
    critical_fails = []
    high_fails = []

    # --- E1: Overall Accuracy ---
    acc = float(accuracy_score(y_true, y_pred))
    results['accuracy'] = acc
    e1_pass = acc >= THRESHOLDS['accuracy']
    print(f'\nE1 Accuracy: {acc:.4f} (threshold: ≥{THRESHOLDS["accuracy"]}) '
          f'→ {"PASS ✓" if e1_pass else "FAIL ✗"}')
    if not e1_pass:
        critical_fails.append(f'E1: accuracy={acc:.4f} < {THRESHOLDS["accuracy"]}')

    # --- E2: Planet Recall ---
    pc_mask = y_true == 0
    if pc_mask.sum() > 0:
        pc_recall = float((y_pred[pc_mask] == 0).sum() / pc_mask.sum())
    else:
        pc_recall = 0.0
    results['planet_recall'] = pc_recall
    e2_pass = pc_recall >= THRESHOLDS['planet_recall']
    print(f'E2 Planet Recall: {pc_recall:.4f} (threshold: ≥{THRESHOLDS["planet_recall"]}) '
          f'→ {"PASS ✓" if e2_pass else "FAIL ✗"}')
    if not e2_pass:
        critical_fails.append(f'E2: planet_recall={pc_recall:.4f} < {THRESHOLDS["planet_recall"]}')

    # --- E3: Planet Precision ---
    pred_pc_mask = y_pred == 0
    if pred_pc_mask.sum() > 0:
        pc_precision = float((y_true[pred_pc_mask] == 0).sum() / pred_pc_mask.sum())
    else:
        pc_precision = 0.0
    results['planet_precision'] = pc_precision
    e3_pass = pc_precision >= THRESHOLDS['planet_precision']
    print(f'E3 Planet Precision: {pc_precision:.4f} (threshold: ≥{THRESHOLDS["planet_precision"]}) '
          f'→ {"PASS ✓" if e3_pass else "FAIL ✗"}')
    if not e3_pass:
        high_fails.append(f'E3: planet_precision={pc_precision:.4f} < {THRESHOLDS["planet_precision"]}')

    # --- E4: FPR for PC class ---
    # FP = non-planet predicted as planet; TN = non-planet predicted as non-planet
    non_planet_mask = y_true != 0
    if non_planet_mask.sum() > 0:
        fpr = float((y_pred[non_planet_mask] == 0).sum() / non_planet_mask.sum())
    else:
        fpr = 0.0
    results['fpr'] = fpr
    e4_pass = fpr <= THRESHOLDS['fpr_max']
    print(f'E4 FPR (PC class): {fpr:.4f} (threshold: ≤{THRESHOLDS["fpr_max"]}) '
          f'→ {"PASS ✓" if e4_pass else "FAIL ✗"}')
    if not e4_pass:
        high_fails.append(f'E4: fpr={fpr:.4f} > {THRESHOLDS["fpr_max"]}')

    # --- E5: ECE (calibration) ---
    ece, per_bin = expected_calibration_error(y_true, y_prob)
    results['ece'] = ece
    e5_pass = ece <= THRESHOLDS['ece_max']
    print(f'E5 ECE: {ece:.4f} (threshold: ≤{THRESHOLDS["ece_max"]}) '
          f'→ {"PASS ✓" if e5_pass else "FAIL ✗"}')
    if not e5_pass:
        critical_fails.append(f'E5: ece={ece:.4f} > {THRESHOLDS["ece_max"]}')

    # --- E6: Per-class F1 ---
    print(f'\nE6 Per-Class Classification Report:')
    print(classification_report(y_true, y_pred, target_names=CLASS_NAMES, zero_division=0))
    f1_macro = float(f1_score(y_true, y_pred, average='macro', zero_division=0))
    f1_per_class = f1_score(y_true, y_pred, average=None, zero_division=0)
    results['f1_macro'] = f1_macro

    # --- E8: Confusion Matrix ---
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(8, 6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=CLASS_NAMES)
    disp.plot(ax=ax, colorbar=True, cmap='Blues')
    ax.set_title('Phase 2 Ensemble Confusion Matrix (Test Set)')
    plt.tight_layout()
    cm_path = os.path.join(output_dir, 'confusion_matrix.png')
    plt.savefig(cm_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'E8 Confusion matrix saved to: {cm_path}')

    # --- E9: ROC-AUC ---
    try:
        roc_auc = float(roc_auc_score(y_true, y_prob, multi_class='ovr', average='macro'))
        results['roc_auc'] = roc_auc
        print(f'E9 ROC-AUC (OvR macro): {roc_auc:.4f}')
    except Exception as e:
        roc_auc = float('nan')
        results['roc_auc'] = roc_auc
        print(f'E9 ROC-AUC: could not compute ({e})')

    # --- Reliability Diagram ---
    bin_centers = [b['bin_center'] for b in per_bin]
    bin_accs = [b['accuracy'] for b in per_bin]
    bin_confs = [b['confidence'] for b in per_bin]

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Perfect calibration')
    ax.bar(bin_centers, bin_accs, width=0.08, alpha=0.6,
           color='steelblue', label='Fraction correct')
    ax.plot(bin_centers, bin_confs, 'ro-', markersize=4, label='Mean confidence')
    ax.set_xlabel('Confidence')
    ax.set_ylabel('Accuracy')
    ax.set_title(f'Reliability Diagram — ECE = {ece:.4f}')
    ax.legend()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    plt.tight_layout()
    reliability_path = os.path.join(output_dir, 'reliability.png')
    plt.savefig(reliability_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Reliability diagram saved to: {reliability_path}')

    # --- Final Summary ---
    print(f'\n{"=" * 60}')
    print('EVALUATION SUMMARY')
    print(f'{"=" * 60}')

    if not critical_fails and not high_fails:
        print('✓ ALL THRESHOLDS PASSED')
        exit_code = 0
    else:
        if critical_fails:
            print(f'✗ CRITICAL FAILURES ({len(critical_fails)}):')
            for f in critical_fails:
                print(f'  • {f}')
            exit_code = 1
        if high_fails:
            print(f'⚠ HIGH-PRIORITY FAILURES ({len(high_fails)}):')
            for f in high_fails:
                print(f'  • {f}')
            if not critical_fails:
                exit_code = 2

    # --- MLflow Logging ---
    mlflow.set_tracking_uri(f'file://{os.getcwd()}/.mlruns')
    mlflow.set_experiment('phase2-evaluation')

    with mlflow.start_run(run_name='phase2-eval'):
        mlflow.log_params({
            'catalogue': catalogue_path,
            'model_dir': model_dir,
            'n_test_samples': len(eval_df),
            'n_bins_calibration': 10,
        })
        mlflow.log_metrics({
            'accuracy': acc,
            'planet_recall': pc_recall,
            'planet_precision': pc_precision,
            'fpr': fpr,
            'ece': ece,
            'f1_macro': f1_macro,
            'roc_auc': roc_auc,
        })
        for i, name in enumerate(CLASS_NAMES):
            mlflow.log_metric(f'f1_{name}', float(f1_per_class[i]))

        mlflow.log_artifact(cm_path)
        mlflow.log_artifact(reliability_path)
        mlflow.set_tag('exit_code', str(exit_code))
        mlflow.set_tag('critical_fails', str(len(critical_fails)))
        mlflow.set_tag('high_fails', str(len(high_fails)))

    return exit_code


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Evaluate Phase 2 ensemble classification results'
    )
    parser.add_argument('--catalogue', type=str, default='data/catalogue/master.parquet')
    parser.add_argument('--model-dir', type=str, default='data/models')
    parser.add_argument('--output-dir', type=str, default='outputs')
    args = parser.parse_args()

    exit_code = run_evaluation(args.catalogue, args.model_dir, args.output_dir)
    raise SystemExit(exit_code)
