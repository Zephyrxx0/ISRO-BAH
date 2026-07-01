"""On-the-fly 7x augmented data generator for CNN training."""

import math
import numpy as np
import tensorflow as tf


class TransitDataGenerator(tf.keras.utils.Sequence):
    """Keras Sequence generator with 7x augmentation (ADR-0003).

    Augmentation pipeline (applied per sample, random choice):
        0: Original (no change)
        1: Gaussian noise injection (sigma = median_flux_err)
        2: Transit time jitter (shift ±5 indices)
        3-6: Synthetic transit injection (batman-like dip at 50-200 ppm)

    The generator produces batches of [global_views, local_views] arrays
    suitable for the Dual-View AstroNet CNN model.

    Args:
        df: DataFrame with columns 'folded_path' and 'label' (int 0-3).
            Optional columns for augmentation: 'median_flux_err',
            'tls_period', 'tls_duration'.
        batch_size: Samples per batch.
        augment: Whether to apply augmentation (True for train, False for val/test).
        shuffle: Whether to shuffle indices each epoch.
    """

    def __init__(self, df, batch_size: int = 32, augment: bool = False,
                 shuffle: bool = True):
        self.df = df.reset_index(drop=True)
        self.batch_size = batch_size
        self.augment = augment
        self.shuffle = shuffle
        self.indices = np.arange(len(self.df))
        self.on_epoch_end()

    def __len__(self) -> int:
        return math.ceil(len(self.df) / self.batch_size)

    def __getitem__(self, idx: int):
        start = idx * self.batch_size
        end = min(start + self.batch_size, len(self.df))
        batch_indices = self.indices[start:end]

        global_views, local_views, labels = [], [], []

        for i in batch_indices:
            row = self.df.iloc[i]
            folded = np.load(row['folded_path'])
            gv = folded['global'].astype(np.float32)
            lv = folded['local'].astype(np.float32)

            if self.augment:
                gv, lv = self._apply_augmentation(gv, lv, row)

            global_views.append(gv.reshape(-1, 1))
            local_views.append(lv.reshape(-1, 1))
            labels.append(row['label'])

        return (
            [np.array(global_views, dtype=np.float32),
             np.array(local_views, dtype=np.float32)],
            np.array(labels, dtype=np.int32),
        )

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)

    def _apply_augmentation(self, gv: np.ndarray, lv: np.ndarray,
                            row) -> tuple:
        """Apply one of 7 augmentation strategies (random choice).

        Args:
            gv: Global view array (2001,).
            lv: Local view array (201,).
            row: DataFrame row with optional metadata columns.

        Returns:
            Augmented (global_view, local_view) tuple.
        """
        choice = np.random.randint(0, 7)

        if choice == 0:
            return gv, lv
        elif choice == 1:
            sigma = row.get('median_flux_err', 0.001)
            noise_g = np.random.normal(0, sigma, gv.shape).astype(np.float32)
            noise_l = np.random.normal(0, sigma, lv.shape).astype(np.float32)
            return gv + noise_g, lv + noise_l
        elif choice == 2:
            # Bug #6 Fix: Use interpolation-based shift instead of np.roll
            # to avoid edge wrapping artifacts
            shift = np.random.randint(-5, 6)
            return self._shift_view(gv, shift), self._shift_view(lv, shift)
        else:
            # Choices 3-6: synthetic transit injection at 50-200 ppm
            depth = np.random.uniform(50e-6, 200e-6)
            return self._inject_synthetic(gv, lv, depth, row)

    @staticmethod
    def _shift_view(view: np.ndarray, shift: int) -> np.ndarray:
        """Shift view by interpolation instead of rolling (Bug #6 fix).
        
        This avoids the edge wrapping artifact where transit dips at one
        edge reappear at the other edge of the phase-folded view.
        
        Args:
            view: Input view array.
            shift: Number of indices to shift (positive = right).
            
        Returns:
            Shifted view with edge padding instead of wrapping.
        """
        if shift == 0:
            return view
        
        result = np.zeros_like(view)
        if shift > 0:
            # Shift right: pad left edge with first value
            result[shift:] = view[:-shift]
            result[:shift] = view[0]
        else:
            # Shift left: pad right edge with last value
            result[:shift] = view[-shift:]
            result[shift:] = view[-1]
        
        return result

    def _inject_synthetic(self, gv: np.ndarray, lv: np.ndarray,
                          depth: float, row) -> tuple:
        """Inject a Gaussian-approximated transit dip at random phase.

        Bug #5 Fix: The depth parameter is in fractional flux (50-200 ppm),
        but the normalized views have median=0 and min≈-1. We scale the
        injection depth relative to the typical transit depth in the view.
        
        For normalized views: a 200ppm transit corresponds to ~0.02% of the
        star's flux. Since views are normalized to min=-1 (deepest transit),
        we inject at 5-20% of that depth to simulate shallow additional transits.

        Args:
            gv: Global view array (normalized: median=0, min≈-1).
            lv: Local view array (normalized: median=0, min≈-1).
            depth: Transit depth in fractional flux units (50-200 ppm).
            row: DataFrame row with tls_period, tls_duration metadata.

        Returns:
            Augmented (global_view, local_view) tuple.
        """
        period = row.get('tls_period', 3.0)
        duration = row.get('tls_duration', 0.1)
        
        # Bug #5 Fix: Scale depth relative to the view's depth range
        # In normalized views: typical transit depth ~ -1.0
        # We inject at 5-20% of typical depth to simulate shallow planets
        view_depth = abs(np.min(lv)) if np.min(lv) < -0.01 else 0.5
        scaled_depth = view_depth * (depth / 100e-6)  # Scale: 100ppm -> 1x view_depth
        scaled_depth = np.clip(scaled_depth, 0.05, 0.25)  # Clamp to 5-25% of view depth
        
        # Duration as fraction of global view length
        dur_bins = max(5, int((duration / period) * len(gv)))
        sigma = dur_bins / 4.0

        # Random center position for global view (avoid edges)
        center_g = np.random.randint(dur_bins, len(gv) - dur_bins)
        t_g = np.arange(len(gv), dtype=np.float32)
        dip_g = -scaled_depth * np.exp(-0.5 * ((t_g - center_g) / sigma) ** 2)
        gv_aug = gv + dip_g

        # Corresponding injection in local view (centered)
        center_l = len(lv) // 2
        t_l = np.arange(len(lv), dtype=np.float32)
        sigma_l = max(3, dur_bins // 4)
        dip_l = -scaled_depth * np.exp(-0.5 * ((t_l - center_l) / sigma_l) ** 2)
        lv_aug = lv + dip_l

        return gv_aug.astype(np.float32), lv_aug.astype(np.float32)
