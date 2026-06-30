"""Ensemble predictor: 0.6*CNN + 0.4*XGBoost with temperature scaling (D-11)."""

import numpy as np
import pandas as pd
import tensorflow as tf
import xgboost as xgb
from pathlib import Path
from tqdm import tqdm

from src.phase2.temperature_scaler import TemperatureScaler
from src.phase2.centroid_analyzer import CROWDSAP_BLOCK_THRESHOLD


CNN_WEIGHT = 0.6
XGB_WEIGHT = 0.4

FEATURE_COLUMNS = [
    'odd_even_depth_diff', 'secondary_eclipse_depth', 'centroid_shift_sigma',
    'v_shape_metric', 'crowdsap', 'duration_period_ratio', 'tls_sde', 'tls_snr',
]

CLASS_NAMES = ['PC', 'EB', 'Blend', 'StellarVar']


def assign_tier(pc_confidence: float) -> str:
    """Assign Gold/Silver/Bronze confidence tier based on PC probability.

    Tiers (D-14):
        Gold:   confidence_pc > 0.90  — highest priority for Phase 3 MCMC
        Silver: confidence_pc > 0.70  — secondary priority
        Bronze: confidence_pc <= 0.70 — low confidence, require manual review

    Args:
        pc_confidence: Calibrated probability of Planet Candidate class [0,1].

    Returns:
        Tier string: 'Gold', 'Silver', or 'Bronze'.
    """
    if pc_confidence > 0.90:
        return 'Gold'
    elif pc_confidence > 0.70:
        return 'Silver'
    else:
        return 'Bronze'


class EnsemblePredictor:
    """Load CNN + XGBoost, combine 0.6/0.4, apply temperature scaling.

    Combines predictions in log-space for numerical stability:
        ensemble_logits = 0.6 * log(cnn_probs) + 0.4 * log(xgb_probs)
    Temperature scaling is applied to the combined logits for calibration.

    CROWDSAP gate (FEAT-03): candidates with crowdsap < 0.5 cannot be
    classified as Planet Candidate regardless of CNN/XGBoost output.

    Args:
        cnn_path: Path to cnn_finetuned.h5.
        xgb_path: Path to xgboost_ensemble.json.
        temperature_path: Path to temperature_scalar.npz.
    """

    def __init__(self, cnn_path: str, xgb_path: str, temperature_path: str):
        # Load CNN
        self.cnn = tf.keras.models.load_model(cnn_path, compile=False)
        # Verify CNN output shape (G5 guardrail)
        dummy_g = np.zeros((1, 2001, 1), dtype=np.float32)
        dummy_l = np.zeros((1, 201, 1), dtype=np.float32)
        test_out = self.cnn.predict([dummy_g, dummy_l], verbose=0)
        assert test_out.shape == (1, 4), f'CNN output shape mismatch: {test_out.shape}'

        # Load XGBoost
        self.xgb_clf = xgb.XGBClassifier()
        self.xgb_clf.load_model(xgb_path)

        # Load temperature scaler
        self.scaler = TemperatureScaler.load(temperature_path)

        # Verify ensemble weights sum to 1.0 (G7 guardrail)
        assert abs(CNN_WEIGHT + XGB_WEIGHT - 1.0) < 1e-6

    def predict_single(self, global_view: np.ndarray, local_view: np.ndarray,
                       tabular_features: np.ndarray) -> np.ndarray:
        """Produce calibrated 4-class probabilities for one candidate.

        Args:
            global_view: (1, 2001, 1) phase-folded global view.
            local_view: (1, 201, 1) phase-folded local view.
            tabular_features: (1, 8) engineered feature vector.

        Returns:
            (4,) calibrated probability array [PC, EB, Blend, StellarVar].
        """
        cnn_probs = self.cnn.predict([global_view, local_view], verbose=0)
        xgb_probs = self.xgb_clf.predict_proba(tabular_features)

        # Combine in log-space for numerical stability
        ensemble_logits = (
            CNN_WEIGHT * np.log(cnn_probs + 1e-10) +
            XGB_WEIGHT * np.log(xgb_probs + 1e-10)
        )

        # Temperature scaling
        calibrated = self.scaler.predict_proba(ensemble_logits)
        return calibrated[0]

    def classify_all(self, catalogue_path: str) -> None:
        """Run ensemble classification on all SDE>=5 candidates.

        Updates master Parquet with columns: predicted_class, confidence_pc,
        prob_EB, prob_Blend, prob_StellarVar, confidence_tier.

        Args:
            catalogue_path: Path to master.parquet.
        """
        df = pd.read_parquet(catalogue_path)
        sde5 = df[df['tls_sde'] >= 5]
        errors = []

        for idx in tqdm(sde5.index, desc='Ensemble classification'):
            row = df.loc[idx]
            try:
                folded_path = row.get('folded_path')
                if not folded_path or not Path(str(folded_path)).exists():
                    continue

                folded = np.load(str(folded_path))
                gv = folded['global'].reshape(1, -1, 1).astype(np.float32)
                lv = folded['local'].reshape(1, -1, 1).astype(np.float32)
                tab = np.array([[
                    row.get(col, 0.0) for col in FEATURE_COLUMNS
                ]], dtype=np.float32)

                probs = self.predict_single(gv, lv, tab)

                # CROWDSAP gate (FEAT-03): block PC if contamination > 0.5
                crowdsap = row.get('crowdsap', 1.0)
                if crowdsap < CROWDSAP_BLOCK_THRESHOLD and np.argmax(probs) == 0:
                    # Redistribute PC probability to other classes
                    probs[0] = 0.0
                    probs = probs / (probs.sum() + 1e-10)

                predicted_class = int(np.argmax(probs))
                pc_confidence = float(probs[0])

                df.loc[idx, 'predicted_class'] = predicted_class
                df.loc[idx, 'confidence_pc'] = pc_confidence
                df.loc[idx, 'prob_EB'] = float(probs[1])
                df.loc[idx, 'prob_Blend'] = float(probs[2])
                df.loc[idx, 'prob_StellarVar'] = float(probs[3])
                df.loc[idx, 'confidence_tier'] = assign_tier(pc_confidence)

            except Exception as e:
                errors.append({'tic_id': row.get('tic_id'), 'error': str(e)})

        df.to_parquet(catalogue_path)

        classified = len(sde5) - len(errors)
        gold_count = (df['confidence_tier'] == 'Gold').sum()
        silver_count = (df['confidence_tier'] == 'Silver').sum()
        print(f'✓ Classification complete: {classified} candidates. '
              f'Gold={gold_count}, Silver={silver_count}')
        if errors:
            print(f'⚠ {len(errors)} candidates failed classification.')
