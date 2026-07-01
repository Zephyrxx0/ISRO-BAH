"""Temperature scaling for ensemble calibration (CONF-01).

Learns a single scalar T that softens overconfident softmax outputs:
    calibrated_probs = softmax(logits / T)

T > 1 softens (reduces overconfidence), T < 1 sharpens, T = 1 is identity.
"""

import numpy as np
from scipy.optimize import minimize
from pathlib import Path


class TemperatureScaler:
    """Learn and apply temperature scaling on ensemble logits.

    Temperature scaling (Guo et al. 2017) is a post-hoc calibration method
    that learns a single scalar temperature T on a held-out calibration set.
    It does not change the model's predictions (argmax is preserved), only
    the confidence values.

    Attributes:
        temperature: Learned scalar T (default 1.0 = no scaling).
    """

    def __init__(self):
        self.temperature = 1.0

    def fit(self, logits: np.ndarray, labels: np.ndarray) -> 'TemperatureScaler':
        """Learn T on calibration set via NLL minimization.

        Args:
            logits: (N, 4) raw ensemble output (log-space combined probabilities).
            labels: (N,) integer class labels 0-3.

        Returns:
            self (fitted).
        """
        result = minimize(
            self._nll_loss, x0=np.array([1.5]),
            args=(logits, labels),
            method='L-BFGS-B', bounds=[(0.01, 10.0)],
        )
        self.temperature = float(result.x[0])
        return self

    def predict_proba(self, logits: np.ndarray) -> np.ndarray:
        """Apply temperature scaling and return calibrated probabilities.

        Args:
            logits: (N, 4) raw ensemble logits.

        Returns:
            (N, 4) calibrated softmax probabilities.
        """
        scaled = logits / self.temperature
        # Numerical stability: subtract max per row
        shifted = scaled - np.max(scaled, axis=1, keepdims=True)
        exp_scaled = np.exp(shifted)
        return exp_scaled / exp_scaled.sum(axis=1, keepdims=True)

    def save(self, path: str = 'data/models/temperature_scalar.npz') -> None:
        """Save temperature to .npz file.

        Args:
            path: Destination path for the temperature artifact.
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, T=np.array([self.temperature]))

    @classmethod
    def load(cls, path: str = 'data/models/temperature_scalar.npz') -> 'TemperatureScaler':
        """Load temperature from .npz file.

        Args:
            path: Source path for the temperature artifact.

        Returns:
            Fitted TemperatureScaler instance.
        """
        scaler = cls()
        data = np.load(path)
        scaler.temperature = float(data['T'][0])
        return scaler

    @staticmethod
    def _nll_loss(T: np.ndarray, logits: np.ndarray, labels: np.ndarray) -> float:
        """Negative log-likelihood loss for temperature optimization.

        Args:
            T: Temperature scalar (length-1 array for scipy minimize).
            logits: (N, 4) raw logits.
            labels: (N,) integer class labels.

        Returns:
            Mean NLL across samples.
        """
        scaled = logits / T[0]
        shifted = scaled - np.max(scaled, axis=1, keepdims=True)
        log_sum_exp = np.log(np.sum(np.exp(shifted), axis=1))
        nll = -np.mean(shifted[np.arange(len(labels)), labels] - log_sum_exp)
        return nll
