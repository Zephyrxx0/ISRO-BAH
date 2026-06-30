"""Dual-View AstroNet CNN model factory for transit classification."""

import tensorflow as tf
from tensorflow.keras import layers, models, Input


def build_astronet_dual_view(
    global_len: int = 2001,
    local_len: int = 201,
    num_classes: int = 4,
) -> models.Model:
    """Build Dual-View AstroNet CNN for transit classification.

    Architecture follows Shallue & Vanderburg 2018 (AJ 155, 94) adapted for
    4-class output: Planet Candidate, Eclipsing Binary, Background Blend,
    Stellar Variability.

    Global tower: 6 Conv1D layers (16→32→64→128→256→512 filters, kernel=5,
    padding='same', MaxPooling(5, strides=2)), ending in GlobalMaxPooling1D.

    Local tower: 4 Conv1D layers (16→32→64→128 filters, same pattern),
    ending in GlobalMaxPooling1D.

    Merged: Dense(512, relu) → Dropout(0.5) → Dense(256, relu) → Dropout(0.3)
    → Dense(num_classes, softmax, dtype=float32).

    Args:
        global_len: Length of global phase-folded view (default 2001).
        local_len: Length of local transit zoom view (default 201).
        num_classes: Number of output classes (default 4).

    Returns:
        Keras Model with inputs ['global_view', 'local_view'] and
        4-class softmax output (float32).
    """
    # --- Global View Tower (2001 points) ---
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

    # --- Local View Tower (201 points) ---
    local_input = Input(shape=(local_len, 1), name='local_view')

    l = layers.Conv1D(16, 5, activation='relu', padding='same')(local_input)
    l = layers.MaxPooling1D(5, strides=2)(l)
    l = layers.Conv1D(32, 5, activation='relu', padding='same')(l)
    l = layers.MaxPooling1D(5, strides=2)(l)
    l = layers.Conv1D(64, 5, activation='relu', padding='same')(l)
    l = layers.MaxPooling1D(5, strides=2)(l)
    l = layers.Conv1D(128, 5, activation='relu', padding='same')(l)
    l = layers.GlobalMaxPooling1D()(l)

    # --- Merge + Classification Head ---
    merged = layers.Concatenate()([g, l])
    x = layers.Dense(512, activation='relu')(merged)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.3)(x)

    # Final layer MUST be float32 under mixed_float16 policy
    output = layers.Dense(
        num_classes, activation='softmax', dtype='float32', name='class_probs'
    )(x)

    model = models.Model(
        inputs=[global_input, local_input],
        outputs=output,
        name='astronet_dual_view',
    )
    return model
