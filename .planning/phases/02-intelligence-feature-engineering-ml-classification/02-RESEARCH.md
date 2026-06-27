# Phase 2: Intelligence — Research

**Researched:** 2026-06-28
**Phase:** Feature Engineering & ML Classification
**Requirement IDs:** FEAT-01..04, CLAS-01..07, CONF-01..03, MLOP-01..02

## 1. AstroNet Dual-View CNN Architecture

### Key Findings

The AstroNet architecture (Shallue & Vanderburg 2018, AJ 155, 94) processes two 1D time-series inputs through separate convolutional towers before merging for classification. The original paper uses:

**Global View Tower (2001 points):**
- Conv1D(16, kernel=5) → MaxPool(5, stride=2)
- Conv1D(32, kernel=5) → MaxPool(5, stride=2)
- Conv1D(64, kernel=5) → MaxPool(5, stride=2)
- Conv1D(128, kernel=5) → MaxPool(5, stride=2)
- Conv1D(256, kernel=5) → MaxPool(5, stride=2)
- Conv1D(512, kernel=5) → GlobalMaxPool → (512,)

**Local View Tower (201 points):**
- Conv1D(16, kernel=5) → MaxPool(5, stride=2)
- Conv1D(32, kernel=5) → MaxPool(5, stride=2)
- Conv1D(64, kernel=5) → MaxPool(5, stride=2)
- Conv1D(128, kernel=5) → GlobalMaxPool → (128,)

**Merged Head:**
- Concatenate → (640,)
- Dense(512, relu) → Dropout(0.5)
- Dense(256, relu) → Dropout(0.3)
- Dense(4, softmax, dtype=float32) — **modified from binary to 4-class**

The Osborn et al. 2020 (A&A 633, A53) adaptation for TESS uses the same architecture with notation: `CONV(kernel_size, num_filters)` → `MAXPOOL(kernel_size, stride)`. Their Figure 2 confirms the layer pattern above.

**Parameter count:** ~250K–300K parameters total. Fits comfortably in T4 16GB VRAM.

**Key adaptation from original:** The original AstroNet outputs binary (planet vs not-planet). Our 4-class output (PC, EB, Blend, StellarVar) replaces the final sigmoid with a 4-unit softmax. This requires the Kepler pre-training to also use 4-class output from the start (not binary → 4-class transfer).

### Implementation Approach

```python
import tensorflow as tf
from tensorflow.keras import layers, models, Input

def build_astronet_dual_view(global_len=2001, local_len=201, num_classes=4):
    # Global View Tower
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

    # Local View Tower
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
    output = layers.Dense(num_classes, activation='softmax', dtype='float32')(x)

    return models.Model(inputs=[global_input, local_input], outputs=output)
```

**Critical implementation notes:**
- `padding='same'` ensures output length matches input for each conv layer (before pooling)
- `dtype='float32'` on final Dense is **mandatory** under `mixed_float16` policy — prevents precision loss in softmax
- MaxPooling stride=2 (not stride=5 as some sources suggest) — TESS 2-min cadence needs gentler downsampling than Kepler 30-min
- ReLU activation throughout (no BatchNorm in original AstroNet — dropout is the primary regularizer)

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| 4-class softmax converges slower than binary | Training may need 2× more epochs | Use class weights; start with higher LR (3e-4) then decay |
| Overfitting on small ExoFOP label set (~5k samples before augmentation) | Poor generalization | 7× augmentation + Dropout(0.5/0.3) + early stopping (patience=10) |
| Mixed precision causing NaN in loss | Training crash | Use `tf.keras.mixed_precision.LossScaleOptimizer`; monitor for NaN per batch |
| Model too simple for Blend vs StellarVar distinction | Low F1 on minority classes | Ensemble with XGBoost compensates — CNN handles morphology, XGBoost handles tabular features |


## 2. Kepler DR24 Pre-Training

### Key Findings

**Dataset:** Kepler DR24 TCE catalog contains 34,032 Threshold Crossing Events from Thompson et al. 2018 (ApJS 235, 38). Available via NASA Exoplanet Archive TAP service.

**Download method:**
```python
from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

# Query the Kepler TCE table (Q1-Q17 DR24)
tce_table = NasaExoplanetArchive.query_criteria(
    table='tcephased',  # or use 'q1_q17_dr24_tce'
    select='kepid,tce_plnt_num,tce_period,tce_time0bk,tce_duration,tce_depth,tce_prad,av_training_set',
    where="av_training_set IS NOT NULL"
)
```

Alternative direct download via TAP:
```
https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=
SELECT+kepid,tce_plnt_num,tce_period,tce_time0bk,tce_duration,tce_depth,av_training_set
+FROM+q1_q17_dr24_tce+WHERE+av_training_set+IS+NOT+NULL&format=csv
```

**Label mapping to 4 classes:**
The `av_training_set` column from the Autovetter training set provides labels. Map as follows:

| Kepler Label | Our Class | Label ID | Approximate Count |
|---|---|---|---|
| `PC` (Planet Candidate) | Planet Candidate | 0 | ~4,000 |
| `AFP` (Astrophysical FP — EB) | Eclipsing Binary | 1 | ~6,000 |
| `NTP` (Non-Transiting Phenomenon) | Stellar Variability | 3 | ~18,000 |
| `UNK` or centroid-flagged | Background Blend | 2 | ~6,000 |

**Note:** The Blend class requires careful construction — Kepler's `koi_fpflag_co` (centroid offset flag) identifies blend-like signals. TCEs with `koi_fpflag_co=1` AND `koi_fpflag_ec=0` should map to Blend (class 2). TCEs with `koi_fpflag_ec=1` (secondary eclipse present) → EB (class 1).

**Light curve data:** Kepler PDCSAP flux from MAST. The google-research/exoplanet-ml repo provides preprocessing scripts that:
1. Download Kepler light curves via `lightkurve.search_lightcurve(f'KIC {kepid}', mission='Kepler')`
2. Phase-fold at TCE period/epoch
3. Bin to 2001 global + 201 local views
4. Normalize: median=0, min=-1

### Implementation Approach

**`train_kepler.py` — standalone prep-week script:**

```python
# Runs ONCE during 7-day prep window. NOT during hackathon.
import tensorflow as tf
from tensorflow.keras import mixed_precision
mixed_precision.set_global_policy('mixed_float16')

# 1. Load pre-processed Kepler phase-folded views
#    (generated by a separate kepler_data_prep.py script)
kepler_data = np.load('data/kepler/kepler_dr24_folded.npz')
global_views = kepler_data['global_views']  # (34032, 2001, 1)
local_views = kepler_data['local_views']    # (34032, 201, 1)
labels = kepler_data['labels']              # (34032,) — 0,1,2,3

# 2. Train/val split (80/20 stratified)
from sklearn.model_selection import train_test_split
idx_train, idx_val = train_test_split(
    np.arange(len(labels)), test_size=0.2, stratify=labels, random_state=42
)

# 3. Build model
model = build_astronet_dual_view(num_classes=4)
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss='sparse_categorical_crossentropy',
    metrics=['sparse_categorical_accuracy']
)

# 4. Train
model.fit(
    [global_views[idx_train], local_views[idx_train]], labels[idx_train],
    validation_data=([global_views[idx_val], local_views[idx_val]], labels[idx_val]),
    batch_size=64, epochs=30,
    callbacks=[
        tf.keras.callbacks.ModelCheckpoint(
            'data/models/kepler_pretrained.h5',
            save_best_only=True, monitor='val_loss'
        ),
        tf.keras.callbacks.EarlyStopping(patience=7, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=3),
    ]
)
```

**Training hyperparameters (pre-training):**
- Batch size: 64 (34k samples fits easily in memory)
- Optimizer: Adam, LR=1e-3 with ReduceLROnPlateau
- Epochs: 30 max (early stopping at patience=7)
- Loss: sparse_categorical_crossentropy
- Mixed precision: float16 compute, float32 output

**Expected training time on T4:** ~2-3 hours for 30 epochs on 34k samples (batch_size=64, ~530 steps/epoch).

**Layers to freeze during TESS fine-tuning:**
- Freeze first 3 conv layers of each tower (low-level transit shape features transfer well)
- Unfreeze last 3 conv layers + all Dense layers
- Use lower LR (1e-4) for fine-tuning vs 1e-3 for pre-training

```python
# Fine-tuning layer freeze pattern
base_model = tf.keras.models.load_model('data/models/kepler_pretrained.h5', compile=False)

# Freeze early conv layers (first 6 layers of each tower = 3 Conv1D + 3 MaxPool)
for layer in base_model.layers[:12]:  # Global tower early layers
    layer.trainable = False
# Keep later layers trainable for domain adaptation

base_model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),  # Lower LR
    loss='sparse_categorical_crossentropy',
    metrics=['sparse_categorical_accuracy']
)
```

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Kepler DR24 download takes >4 hours | Blocks prep week | Pre-download raw data to `data/kepler/raw/` before prep week starts; use lightkurve bulk download |
| Blend class poorly represented in Kepler | Class imbalance during pre-training | Use centroid-offset-flagged TCEs + class weights during pre-training |
| Domain gap Kepler→TESS too large | Pre-trained features don't transfer | Fine-tune with unfrozen later layers; the 7× augmentation helps bridge the gap |
| Kepler light curves at 30-min cadence vs TESS 2-min | Temporal resolution mismatch | Phase-folding + binning to fixed 2001/201 points normalizes cadence differences |


## 3. TESS ExoFOP Fine-Tuning + 7× Augmentation

### Key Findings

**ExoFOP TOI labels source:** The TESS Objects of Interest (TOI) table is downloadable from:
- Web: https://exofop.ipac.caltech.edu/tess/ → CSV export
- TAP: `https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=SELECT+*+FROM+toi&format=csv`
- Python: `NasaExoplanetArchive.query_criteria(table='toi')`

**Label mapping from ExoFOP TOI dispositions:**
| ExoFOP `tfopwg_disp` | Our Class | Label |
|---|---|---|
| `PC`, `KP`, `CP`, `APC` | Planet Candidate | 0 |
| `EB`, `BEB` | Eclipsing Binary | 1 |
| `FA`, `FP` (with centroid flag) | Background Blend | 2 |
| `V`, `IS`, `O` (other stellar) | Stellar Variability | 3 |

**Expected label counts (Sectors 1-3):** ~2,000–5,000 labeled candidates after cross-matching with our Phase 1 SDE≥5 detections. Minimum viable: 800 samples (200/class).

**7× Augmentation Strategy (ADR-0003):**
Each training sample produces 7 variants per epoch (on-the-fly, not pre-stored):

1. **1× Original** — unmodified phase-folded view
2. **1× Gaussian noise injection** — add N(0, σ) where σ = median per-sample flux error
3. **1× Transit time jitter** — shift the phase-folded view by ±3-5 bin indices (simulates timing uncertainty)
4. **4× Synthetic transit injection** — inject batman-model transits at depths uniformly sampled from [50, 200] ppm

The synthetic injection uses `batman` TransitModel:
```python
import batman

def generate_synthetic_transit(period, duration, depth_ppm, n_points=2001):
    params = batman.TransitParams()
    params.t0 = 0.0
    params.per = period
    params.rp = np.sqrt(depth_ppm * 1e-6)  # Rp/Rs from depth
    params.a = 15.0  # semi-major axis / stellar radius (typical)
    params.inc = 89.5  # near edge-on
    params.ecc = 0.0
    params.w = 90.0
    params.u = [0.3, 0.2]  # quadratic limb darkening
    params.limb_dark = "quadratic"

    t = np.linspace(-0.5, 0.5, n_points) * period  # phase range
    m = batman.TransitModel(params, t)
    flux = m.light_curve(params) - 1.0  # normalize: transit dip is negative
    return flux
```

### Implementation Approach

**Keras `tf.keras.utils.Sequence` data generator:**

```python
class TransitDataGenerator(tf.keras.utils.Sequence):
    def __init__(self, df, batch_size=32, augment=False, shuffle=True):
        self.df = df.reset_index(drop=True)
        self.batch_size = batch_size
        self.augment = augment
        self.shuffle = shuffle
        self.indices = np.arange(len(self.df))
        self.on_epoch_end()

    def __len__(self):
        return int(np.ceil(len(self.df) / self.batch_size))

    def __getitem__(self, idx):
        start = idx * self.batch_size
        end = min(start + self.batch_size, len(self.df))
        batch_idx = self.indices[start:end]

        gv_batch, lv_batch, y_batch = [], [], []
        for i in batch_idx:
            row = self.df.iloc[i]
            data = np.load(row['folded_path'])
            gv, lv = data['global'], data['local']

            if self.augment:
                aug_choice = np.random.randint(0, 7)
                gv, lv = self._augment(gv, lv, aug_choice, row)

            gv_batch.append(gv.reshape(-1, 1))
            lv_batch.append(lv.reshape(-1, 1))
            y_batch.append(row['label'])

        return [np.array(gv_batch), np.array(lv_batch)], np.array(y_batch)

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)

    def _augment(self, gv, lv, choice, row):
        if choice == 0:
            return gv, lv  # original
        elif choice == 1:
            sigma = row.get('median_flux_err', 1e-3)
            return gv + np.random.normal(0, sigma, gv.shape), \
                   lv + np.random.normal(0, sigma, lv.shape)
        elif choice == 2:
            shift = np.random.randint(-5, 6)
            return np.roll(gv, shift), np.roll(lv, shift)
        else:  # choices 3-6: synthetic injection
            depth = np.random.uniform(50e-6, 200e-6)
            synthetic = generate_synthetic_transit(
                row['tls_period'], row['tls_duration'], depth * 1e6, len(gv)
            )
            return gv + synthetic, lv + synthetic[:len(lv)]
```

**Mixed precision setup (mandatory for T4):**
```python
from tensorflow.keras import mixed_precision
mixed_precision.set_global_policy('mixed_float16')
# Reduces VRAM by ~40%. batch_size=32 is safe; batch_size=64 may work.
# ALWAYS verify output layer is float32.
```

**Stratified sampling for class balance:**
```python
from sklearn.utils.class_weight import compute_class_weight

class_weights = compute_class_weight('balanced', classes=np.unique(y), y=y)
class_weight_dict = dict(zip(np.unique(y), class_weights))
# Pass to model.fit(class_weight=class_weight_dict)
```

**Effective training set size with 7× augmentation:**
- If ExoFOP provides 3,000 labeled samples → 21,000 effective samples per epoch
- At batch_size=32: ~656 steps/epoch
- 50 epochs × 656 steps = ~32,800 gradient updates
- Expected training time on T4: ~2-3 hours

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| ExoFOP labels too few for Sectors 1-3 specifically | <200 samples per class | Include labels from all TESS sectors in ExoFOP (not just 1-3) for training; inference is sector-specific |
| Synthetic injection creates unrealistic transits | CNN learns artifacts, not physics | Use batman with realistic limb darkening; randomize orbital parameters within physical bounds |
| 7× augmentation causes GPU OOM | Training crashes | batch_size=32 (not 64); augmentation is on-the-fly (no disk storage); monitor GPU memory |
| Class imbalance after ExoFOP label extraction | Majority class dominates | class_weight + stratified split + F1-macro metric |


## 4. Feature Extraction Pipeline

### Key Findings

Eight core features required by FEAT-01, each targeting specific false positive discrimination:

**Feature 1: Odd/Even Transit Depth Difference**
- Eclipsing binaries have different depths for odd (primary) and even (secondary) transits
- Computation: separate odd-numbered and even-numbered transits, fit depth to each subset
- Metric: `|depth_odd - depth_even| / sqrt(err_odd² + err_even²)` → sigma significance
- Threshold: >3σ difference strongly indicates EB

```python
def compute_odd_even_depth(time, flux, period, t0, duration):
    phase = ((time - t0) % period) / period
    transit_mask = phase < (duration / period) | phase > (1 - duration / period)
    # Separate transits by epoch number
    epoch_num = np.round((time - t0) / period).astype(int)
    odd_mask = transit_mask & (epoch_num % 2 == 1)
    even_mask = transit_mask & (epoch_num % 2 == 0)
    depth_odd = 1.0 - np.median(flux[odd_mask]) if odd_mask.sum() > 3 else np.nan
    depth_even = 1.0 - np.median(flux[even_mask]) if even_mask.sum() > 3 else np.nan
    return depth_odd, depth_even, np.abs(depth_odd - depth_even)
```

**Feature 2: Secondary Eclipse Depth (at phase 0.5)**
- EBs show a secondary eclipse at orbital phase 0.5 (anti-transit)
- Planets may show occultation but typically <50 ppm (undetectable in TESS)
- Computation: measure flux dip in window [0.45, 0.55] of phase

```python
def compute_secondary_eclipse(phase_folded_flux, phase_array):
    sec_mask = (phase_array > 0.45) & (phase_array < 0.55)
    oot_mask = (phase_array > 0.2) & (phase_array < 0.4)
    sec_depth = np.median(phase_folded_flux[oot_mask]) - np.median(phase_folded_flux[sec_mask])
    return max(sec_depth, 0.0)  # Only positive detections
```

**Feature 3: Centroid Shift (TPF-based, FEAT-02)**
- Background blends cause the flux-weighted centroid to shift toward the contaminating source during transit
- Requires Target Pixel File (TPF) data — download via TESScut for top 200 SDE≥7 candidates only
- Computation: flux-weighted centroid (x,y) in-transit vs out-of-transit; distance in pixels

```python
import lightkurve as lk

def compute_centroid_shift(tpf, transit_mask):
    """
    tpf: lightkurve TargetPixelFile
    transit_mask: boolean array (True = in-transit cadences)
    """
    # Flux-weighted centroid for in-transit frames
    in_transit_flux = tpf.flux.value[transit_mask]
    oot_flux = tpf.flux.value[~transit_mask]

    # Compute centroid per frame, then average
    def flux_weighted_centroid(frames):
        ys, xs = np.mgrid[:frames.shape[1], :frames.shape[2]]
        total = frames.sum(axis=(1, 2))
        cx = (frames * xs).sum(axis=(1, 2)) / total
        cy = (frames * ys).sum(axis=(1, 2)) / total
        return np.nanmedian(cx), np.nanmedian(cy)

    cx_in, cy_in = flux_weighted_centroid(in_transit_flux)
    cx_out, cy_out = flux_weighted_centroid(oot_flux)

    shift_pixels = np.sqrt((cx_in - cx_out)**2 + (cy_in - cy_out)**2)
    # Convert to sigma using scatter of OOT centroids
    cx_oot_all, cy_oot_all = flux_weighted_centroid_per_frame(oot_flux)
    sigma = np.std(np.sqrt((cx_oot_all - cx_out)**2 + (cy_oot_all - cy_out)**2))
    shift_sigma = shift_pixels / sigma if sigma > 0 else 0.0
    return shift_pixels, shift_sigma  # >3σ = blend flag
```

**Feature 4: V-Shape Metric**
- Grazing EBs produce V-shaped transits (no flat bottom)
- True planets with short ingress/egress have U-shaped transits
- Metric: `(t_ingress + t_egress) / t_total` — ratio of ingress+egress duration to total duration
- V-shaped: ratio > 0.5; U-shaped (planetary): ratio < 0.3

```python
def compute_v_shape(local_view_201):
    """Compute V-shape from 201-point local view."""
    depth = 1.0 - np.min(local_view_201)
    if depth < 1e-5:
        return 0.0
    half_depth = 1.0 - depth / 2.0
    # Find ingress/egress points (where flux crosses half-depth)
    center = len(local_view_201) // 2
    left_cross = np.where(local_view_201[:center] < half_depth)[0]
    right_cross = np.where(local_view_201[center:] < half_depth)[0]
    if len(left_cross) == 0 or len(right_cross) == 0:
        return 1.0  # V-shaped if no flat bottom found
    ingress_start = left_cross[0]
    egress_end = center + right_cross[-1]
    # Flat bottom = points within 10% of minimum
    flat_mask = local_view_201 < (1.0 - 0.9 * depth)
    flat_duration = np.sum(flat_mask)
    total_duration = egress_end - ingress_start
    return 1.0 - (flat_duration / total_duration) if total_duration > 0 else 1.0
```

**Feature 5: CROWDSAP Contamination (FEAT-03)**
- CROWDSAP = fraction of flux from target star vs total flux in aperture
- CROWDSAP < 0.5 → blocks PC classification (too contaminated)
- CROWDSAP < 0.9 → triggers centroid investigation
- Source: TIC catalog (available in lightkurve target metadata or MAST query)

```python
def get_crowdsap(tic_id, sector):
    """Query CROWDSAP from TESS light curve FITS header."""
    lc = lk.search_lightcurve(f'TIC {tic_id}', sector=sector, author='SPOC')
    if len(lc) > 0:
        lc_file = lc.download()
        return lc_file.meta.get('CROWDSAP', 1.0)
    return 1.0  # Default if unavailable
```

**Feature 6: Duration/Period Ratio**
- Planets: typical ratio 0.01–0.05 (short transit relative to orbit)
- EBs: can have ratio > 0.1 (long eclipses)
- Computation: `tls_duration / tls_period`

**Feature 7 & 8: SDE and SNR**
- Directly from Phase 1 TLS output (already in Parquet)
- SDE: signal detection efficiency from TLS
- SNR: signal-to-noise ratio of transit depth relative to noise

### Implementation Approach

**`FeatureExtractor` class (D-06):**

```python
class FeatureExtractor:
    """Extract 8+ features per candidate. Appends to master Parquet."""

    FEATURE_COLUMNS = [
        'odd_even_depth_diff', 'secondary_eclipse_depth',
        'centroid_shift_sigma', 'v_shape_metric',
        'crowdsap', 'duration_period_ratio', 'tls_sde', 'tls_snr'
    ]

    def __init__(self, catalogue_path, preprocessed_dir, folded_dir):
        self.df = pd.read_parquet(catalogue_path)
        self.preprocessed_dir = preprocessed_dir
        self.folded_dir = folded_dir

    def run_all(self):
        """Extract features for all SDE≥5 candidates."""
        sde5_mask = self.df['tls_sde'] >= 5
        for idx in tqdm(self.df[sde5_mask].index, desc='Extracting features'):
            row = self.df.loc[idx]
            features = self._extract_single(row)
            for col, val in features.items():
                self.df.loc[idx, col] = val
        self.df.to_parquet(self.catalogue_path)

    def _extract_single(self, row):
        data = np.load(row['preprocessed_path'])
        folded = np.load(row['folded_path'])
        return {
            'odd_even_depth_diff': compute_odd_even_depth(
                data['time'], data['flux'], row['tls_period'], row['tls_t0'], row['tls_duration']
            )[2],
            'secondary_eclipse_depth': compute_secondary_eclipse(
                folded['global'], np.linspace(-0.5, 0.5, len(folded['global']))
            ),
            'v_shape_metric': compute_v_shape(folded['local']),
            'crowdsap': row.get('crowdsap', 1.0),
            'duration_period_ratio': row['tls_duration'] / row['tls_period'],
            'tls_sde': row['tls_sde'],
            'tls_snr': row['tls_snr'],
        }
```

**Phase-folding implementation (2001 global + 201 local):**

```python
class PhaseFolder:
    """Generate phase-folded views per candidate (D-08)."""

    def fold_single(self, time, flux, period, t0, duration):
        # Phase fold
        phase = ((time - t0) % period) / period
        phase[phase > 0.5] -= 1.0  # Center transit at phase 0

        # Global view: 2001 bins spanning full orbit [-0.5, 0.5]
        global_bins = np.linspace(-0.5, 0.5, 2002)
        global_view = np.zeros(2001)
        for i in range(2001):
            mask = (phase >= global_bins[i]) & (phase < global_bins[i+1])
            global_view[i] = np.median(flux[mask]) if mask.sum() > 0 else 0.0

        # Local view: 201 bins spanning ±2× transit duration
        half_width = 2.0 * (duration / period)
        local_bins = np.linspace(-half_width, half_width, 202)
        local_view = np.zeros(201)
        for i in range(201):
            mask = (phase >= local_bins[i]) & (phase < local_bins[i+1])
            local_view[i] = np.median(flux[mask]) if mask.sum() > 0 else 0.0

        # Normalize: median=0, min=-1
        global_view -= np.median(global_view)
        if np.min(global_view) != 0:
            global_view /= np.abs(np.min(global_view))

        local_view -= np.median(local_view)
        if np.min(local_view) != 0:
            local_view /= np.abs(np.min(local_view))

        return global_view, local_view
```

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Centroid analysis requires TPF download (slow, rate-limited) | Blocks feature extraction for all candidates | Only download TPFs for top 200 SDE≥7 candidates (D-09); set centroid_shift=0 for others |
| Phase-folding fails for multi-planet systems | Wrong period produces flat/noisy view | Use TLS best-fit period; iterative masking already handled in Phase 1 |
| CROWDSAP not available for all TIC IDs | Missing feature values | Default to 1.0 (no contamination assumed); flag in catalogue |
| Feature extraction on 60k candidates is slow | Hours of compute | CuPy GPU acceleration for array ops (D-07); parallelize with joblib for CPU-bound parts |


## 5. XGBoost Classifier

### Key Findings

XGBoost 3.3 with `multi:softprob` objective produces per-class probabilities for ensemble combination. The tabular features (8+) capture domain knowledge that the CNN's raw light curve input cannot directly encode (e.g., CROWDSAP from catalog, odd/even statistical test).

**Feature matrix:** 8 engineered features per candidate from the master Parquet:
- `odd_even_depth_diff` — EB discriminator (>3σ = EB)
- `secondary_eclipse_depth` — EB discriminator (non-zero = EB)
- `centroid_shift_sigma` — Blend discriminator (>3σ = Blend)
- `v_shape_metric` — EB discriminator (>0.5 = grazing EB)
- `crowdsap` — Blend pre-filter (<0.5 blocks PC)
- `duration_period_ratio` — EB vs PC (EBs have longer relative eclipses)
- `tls_sde` — signal strength (higher = more confident detection)
- `tls_snr` — signal quality (noise-normalized depth)

**XGBoost 3.3 API (scikit-learn compatible):**

```python
import xgboost as xgb

clf = xgb.XGBClassifier(
    objective='multi:softprob',
    num_class=4,
    tree_method='hist',
    device='cuda',           # T4 GPU acceleration
    max_depth=6,
    learning_rate=0.05,
    n_estimators=500,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    reg_lambda=1.0,
    reg_alpha=0.1,
    eval_metric='mlogloss',
    early_stopping_rounds=20,
    random_state=42,
)
```

### Implementation Approach

**Stratified k-fold cross-validation with F1-macro:**

```python
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score
import numpy as np

def train_xgboost_cv(X, y, params, n_splits=5):
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    f1_scores = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        clf = xgb.XGBClassifier(**params)
        clf.fit(
            X[train_idx], y[train_idx],
            eval_set=[(X[val_idx], y[val_idx])],
            verbose=False
        )
        y_pred = clf.predict(X[val_idx])
        f1 = f1_score(y[val_idx], y_pred, average='macro')
        f1_scores.append(f1)

    return np.mean(f1_scores), np.std(f1_scores)
```

**Hyperparameter tuning strategy (hackathon-constrained):**

Given 30-hour hackathon time pressure, use a focused grid search (not random/Bayesian):

```python
# Quick grid — 12 combinations, ~5 min total on T4
param_grid = {
    'max_depth': [4, 6, 8],
    'learning_rate': [0.03, 0.05, 0.1],
    'n_estimators': [300, 500],
}
# Use early_stopping_rounds=20 to auto-select n_estimators
# Best combo typically: depth=6, lr=0.05, n_est=500
```

**SHAP TreeExplainer integration (CLAS-07):**

```python
import shap

explainer = shap.TreeExplainer(clf)
shap_values = explainer.shap_values(X_test)
# shap_values shape for multi-class: list of 4 arrays, each (N, 8)

# Summary bar plot (global feature importance)
shap.summary_plot(
    shap_values, X_test,
    feature_names=FeatureExtractor.FEATURE_COLUMNS,
    plot_type='bar',
    class_names=['PC', 'EB', 'Blend', 'StellarVar'],
    show=False
)
plt.savefig('outputs/shap_summary.png', dpi=150, bbox_inches='tight')

# Per-class beeswarm for PC class
shap.summary_plot(
    shap_values[0], X_test,  # Class 0 = PC
    feature_names=FeatureExtractor.FEATURE_COLUMNS,
    show=False
)
plt.savefig('outputs/shap_pc_beeswarm.png', dpi=150, bbox_inches='tight')
```

**Expected SHAP importance order (domain-informed):**
1. `odd_even_depth_diff` — strongest EB vs PC separator
2. `secondary_eclipse_depth` — definitive EB indicator
3. `centroid_shift_sigma` — Blend discriminator
4. `v_shape_metric` — grazing EB detector
5. `crowdsap` — contamination pre-filter
6. `duration_period_ratio` — EB characteristic
7. `tls_sde` / `tls_snr` — informative but not dominant

If SDE/SNR dominate, the classifier is acting as a signal-strength threshold rather than learning physics.

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Only 8 features → overfitting with deep trees | Memorizes training set | max_depth=6, subsample=0.8, colsample=0.8, reg_lambda=1.0 |
| SHAP values unstable across CV folds | Unreliable feature importance | Compute Kendall's τ between fold rank orders; report instability if τ < 0.6 |
| XGBoost + CNN disagree on many candidates | Confusing ensemble outputs | This is expected for borderline cases; log disagreement rate; flag for manual review |
| Missing centroid_shift for non-TPF candidates | Feature has many zeros | XGBoost handles missing/zero values natively; tree splits can work around it |


## 6. Ensemble & Calibration

### Key Findings

**Weighted ensemble:** `0.6 × CNN_probs + 0.4 × XGBoost_probs`

Rationale for 0.6/0.4 split:
- CNN processes raw phase-folded morphology (2001+201 data points) — richer input signal
- XGBoost processes 8 tabular features — captures domain rules CNN can't directly encode
- 0.6/0.4 follows ExoMiner++ pattern (Valizadegan et al. 2023) where the primary model gets majority weight
- If one model fails to load, the other can still produce predictions (graceful degradation per D-11)

**Temperature scaling (Guo et al. 2017, ICML):**

The ensemble produces raw logits (pre-softmax) that are typically overconfident. Temperature scaling learns a single scalar T > 1 that "softens" the distribution:

```
calibrated_probs = softmax(logits / T)
```

- T is learned by minimizing Negative Log-Likelihood (NLL) on the calibration set (20% split)
- Optimization via scipy L-BFGS-B with bounds [0.01, 10.0]
- Typical T values: 1.2–2.0 for overconfident models; T=1 means already calibrated

**ECE computation (10 equal-width bins):**

```python
def compute_ece(y_true, y_prob, n_bins=10):
    confidences = np.max(y_prob, axis=1)
    predictions = np.argmax(y_prob, axis=1)
    accuracies = (predictions == y_true)

    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (confidences > bin_edges[i]) & (confidences <= bin_edges[i+1])
        if mask.sum() > 0:
            bin_acc = accuracies[mask].mean()
            bin_conf = confidences[mask].mean()
            ece += (mask.sum() / len(y_true)) * abs(bin_acc - bin_conf)
    return ece
```

Target: ECE < 0.04. If raw ensemble ECE > 0.06, temperature scaling should reduce it.

### Implementation Approach

**`TemperatureScaler` class (D-13):**

```python
from scipy.optimize import minimize

class TemperatureScaler:
    def __init__(self):
        self.temperature = 1.0

    def fit(self, logits, labels):
        """Learn T on calibration set via NLL minimization."""
        def nll(T):
            scaled = logits / T[0]
            log_probs = scaled - np.log(np.sum(np.exp(scaled), axis=1, keepdims=True))
            return -np.mean(log_probs[np.arange(len(labels)), labels])

        result = minimize(nll, x0=[1.5], method='L-BFGS-B', bounds=[(0.01, 10.0)])
        self.temperature = result.x[0]
        return self

    def predict_proba(self, logits):
        scaled = logits / self.temperature
        exp_scaled = np.exp(scaled - np.max(scaled, axis=1, keepdims=True))  # numerical stability
        return exp_scaled / exp_scaled.sum(axis=1, keepdims=True)

    def save(self, path='data/models/temperature_scalar.npz'):
        np.savez(path, T=self.temperature)

    @classmethod
    def load(cls, path='data/models/temperature_scalar.npz'):
        scaler = cls()
        scaler.temperature = np.load(path)['T']
        return scaler
```

**`EnsemblePredictor` class (D-11):**

```python
class EnsemblePredictor:
    CNN_WEIGHT = 0.6
    XGB_WEIGHT = 0.4

    def __init__(self, cnn_path, xgb_path, temperature_path):
        self.cnn = tf.keras.models.load_model(cnn_path, compile=False)
        self.xgb = xgb.XGBClassifier()
        self.xgb.load_model(xgb_path)
        self.scaler = TemperatureScaler.load(temperature_path)

    def predict(self, global_view, local_view, tabular_features):
        """Produce calibrated 4-class probabilities."""
        # CNN raw softmax (already probabilities, treat as logits for ensemble)
        cnn_probs = self.cnn.predict([global_view, local_view], verbose=0)
        # XGBoost probabilities
        xgb_probs = self.xgb.predict_proba(tabular_features)
        # Weighted combination (logit space approximation)
        ensemble_logits = self.CNN_WEIGHT * np.log(cnn_probs + 1e-10) + \
                         self.XGB_WEIGHT * np.log(xgb_probs + 1e-10)
        # Temperature scaling
        return self.scaler.predict_proba(ensemble_logits)
```

**Gold/Silver/Bronze tier assignment:**

```python
def assign_tiers(pc_confidence):
    """Assign confidence tiers based on PC class probability."""
    if pc_confidence > 0.90:
        return 'Gold'
    elif pc_confidence > 0.70:
        return 'Silver'
    else:
        return 'Bronze'
```

**Reliability diagram generation:**

```python
from sklearn.calibration import calibration_curve
import matplotlib.pyplot as plt

def plot_reliability_diagram(y_true, y_prob, n_bins=10, save_path='outputs/reliability.png'):
    fig, ax = plt.subplots(1, 1, figsize=(6, 6))
    # Overall calibration
    prob_true, prob_pred = calibration_curve(
        (y_true == 0).astype(int),  # PC class binary
        y_prob[:, 0], n_bins=n_bins, strategy='uniform'
    )
    ax.plot(prob_pred, prob_true, 's-', label='PC class')
    ax.plot([0, 1], [0, 1], 'k--', label='Perfect calibration')
    ax.set_xlabel('Mean predicted probability')
    ax.set_ylabel('Fraction of positives')
    ax.set_title(f'Reliability Diagram (ECE={compute_ece(y_true, y_prob):.4f})')
    ax.legend()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
```

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| CNN outputs already softmax (not raw logits) | Temperature scaling less effective on probabilities | Convert to log-space before ensemble combination; or extract pre-softmax logits via intermediate model |
| Temperature T > 2.0 | Ensemble is severely overconfident pre-calibration | Investigate source: likely overfitting in CNN. Consider increasing dropout, reducing epochs |
| ECE > 0.04 after scaling | Fails CONF-03 requirement | Try per-class temperature (vector T); or use Platt scaling as fallback |
| Gold tier contains false positives | Wastes Phase 3 MCMC compute | Raise Gold threshold to 0.92; add manual centroid check for all Gold candidates |


## 7. MLflow Experiment Tracking

### Key Findings

MLflow 3.14 provides zero-infrastructure local experiment tracking via `.mlruns/` directory. No server required for hackathon use. Two experiments track the full Phase 2 workflow:

**Experiment 1: `kepler-pretrain`**
- Runs during prep week only
- Logs: epochs completed, val_loss, val_accuracy per epoch, training time, GPU memory peak
- Artifacts: `kepler_pretrained.h5`, training curves PNG, model summary text

**Experiment 2: `tess-finetune-xgboost`**
- Runs during hackathon
- Sub-runs: CNN fine-tuning run, XGBoost training run, calibration run, evaluation run
- Logs: all hyperparams, per-epoch metrics, confusion matrix, ECE before/after, SHAP plot
- Artifacts: `cnn_finetuned.h5`, `xgboost_ensemble.json`, `temperature_scalar.npz`

### Implementation Approach

**MLflow setup (no server, local filesystem):**

```python
import mlflow
import os

# Set tracking URI to local .mlruns directory
mlflow.set_tracking_uri(f'file://{os.getcwd()}/.mlruns')

# Common logging pattern
def log_training_run(experiment_name, run_name, params, model, history=None):
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name):
        # Metadata
        mlflow.set_tag('git_commit', get_git_hash())
        mlflow.set_tag('gpu', 'T4')
        mlflow.set_tag('phase', '2-intelligence')

        # Parameters
        mlflow.log_params(params)

        # Metrics (per-epoch for CNN)
        if history:
            for epoch, metrics in enumerate(zip(
                history.history['val_loss'],
                history.history['val_sparse_categorical_accuracy']
            )):
                mlflow.log_metrics({
                    'val_loss': metrics[0],
                    'val_acc': metrics[1]
                }, step=epoch)

        # Model artifact
        mlflow.log_artifact(model_path)
```

**What to log per experiment:**

| Experiment | Parameters | Metrics (per step) | Artifacts |
|---|---|---|---|
| `kepler-pretrain` | batch_size, lr, epochs, optimizer, architecture | val_loss, val_acc, train_loss | kepler_pretrained.h5, training_curves.png |
| `tess-finetune-xgboost` | batch_size, lr, frozen_layers, augmentation, xgb_params | val_loss, val_acc, mlogloss, f1_macro | cnn_finetuned.h5, xgboost_ensemble.json |
| `phase2-evaluation` | temperature_T, ensemble_weights, test_split_size | accuracy, recall, precision, FPR, ECE, ROC-AUC | confusion_matrix.png, reliability.png, shap_summary.png |

**Confusion matrix logging:**

```python
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

cm = confusion_matrix(y_test, y_pred)
disp = ConfusionMatrixDisplay(cm, display_labels=['PC', 'EB', 'Blend', 'StellarVar'])
fig, ax = plt.subplots(figsize=(8, 6))
disp.plot(ax=ax, cmap='Blues', values_format='d')
plt.title('Phase 2 Classification — Confusion Matrix')
plt.savefig('/tmp/confusion_matrix.png', dpi=150, bbox_inches='tight')
mlflow.log_artifact('/tmp/confusion_matrix.png')
mlflow.log_dict(cm.tolist(), 'confusion_matrix.json')
```

**Browsing results (optional, for manual inspection):**
```bash
cd /home/zeph/Code/ISRO
mlflow ui --backend-store-uri .mlruns/ --port 5000
# Open http://localhost:5000 to compare runs
```

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `.mlruns/` directory grows large with model artifacts | Disk space on Colab | Only save best model per experiment (not every epoch); use `save_best_only=True` |
| MLflow autolog conflicts with manual logging | Double-logged artifacts | Disable autolog; use manual logging exclusively |
| Forgetting to log git commit | Can't trace which code produced a model | Add `mlflow.set_tag('git_commit', ...)` to a shared utility function called by all scripts |
| MLflow version mismatch between team members | Corrupted .mlruns | Pin `mlflow==3.14.0` in requirements.txt |


## 8. Integration Points

### Key Findings

**Phase 1 → Phase 2 Data Contract (D-15, D-16):**

Phase 2 reads from Phase 1 outputs with strict schema requirements:

| Input | Path | Format | Required Keys/Columns |
|---|---|---|---|
| Preprocessed light curves | `data/preprocessed/sector{N}/TIC_*_preprocessed.npz` | .npz | `time`, `flux`, `flux_raw`, `flux_err`, `quality_mask`, `sector`, `tic_id` |
| Master catalogue | `data/catalogue/master.parquet` | Parquet | `tic_id`, `sector`, `tess_mag`, `ra`, `dec`, `candidate_num`, `tls_period`, `tls_t0`, `tls_sde`, `tls_snr`, `tls_cdpp`, `tls_depth`, `tls_duration`, `n_valid_cadences`, `preprocessed_path` |

**Phase 2 → Phase 3 Handoff:**

Phase 2 appends these columns to `data/catalogue/master.parquet`:

| Column | Type | Description | Used By Phase 3 |
|---|---|---|---|
| `predicted_class` | int (0-3) | Ensemble classification label | MCMC gating, report |
| `confidence_pc` | float [0,1] | Planet Candidate probability | MCMC gating (>0.85 for full emcee) |
| `confidence_tier` | str | Gold/Silver/Bronze | Phase 3 priority ordering |
| `prob_EB` | float | EB probability | Diagnostic plots |
| `prob_Blend` | float | Blend probability | TPF re-check flag |
| `prob_StellarVar` | float | StellarVar probability | Diagnostic plots |
| `odd_even_depth_diff` | float | Feature: odd/even Δdepth | Report, diagnostic |
| `secondary_eclipse_depth` | float | Feature: sec eclipse | Report, diagnostic |
| `centroid_shift_sigma` | float | Feature: centroid σ | Blend flag, report |
| `v_shape_metric` | float | Feature: V-shape ratio | Report, diagnostic |
| `crowdsap` | float | TIC contamination ratio | CROWDSAP gate |
| `duration_period_ratio` | float | Feature: dur/per | Report |
| `folded_path` | str | Path to phase-folded .npz | Phase 3 plots, inference |

Phase 2 also produces:
- `data/folded/TIC_{id}_folded.npz` — phase-folded views (keys: `global`, `local`)
- `data/models/cnn_finetuned.h5` — trained CNN
- `data/models/xgboost_ensemble.json` — trained XGBoost
- `data/models/temperature_scalar.npz` — calibration temperature

**`run_pipeline.py` integration:**

Phase 2 modules integrate as pipeline steps (feature extraction + inference only — training is manual):

```python
# run_pipeline.py additions for Phase 2
def run_phase2(catalogue_path, sectors, model_dir='data/models'):
    """Phase 2: Feature Engineering & Classification."""
    from src.phase2.validate_phase1 import validate_phase1_outputs
    from src.phase2.feature_extractor import FeatureExtractor
    from src.phase2.phase_folder import PhaseFolder
    from src.phase2.ensemble_predictor import EnsemblePredictor

    # Step 1: Validate Phase 1 outputs exist and are correct
    validate_phase1_outputs(catalogue_path)

    # Step 2: Phase-fold all SDE≥5 candidates
    folder = PhaseFolder(catalogue_path, 'data/preprocessed', 'data/folded')
    folder.run_all()

    # Step 3: Extract engineered features
    extractor = FeatureExtractor(catalogue_path, 'data/preprocessed', 'data/folded')
    extractor.run_all()

    # Step 4: Run ensemble classification (requires pre-trained models)
    predictor = EnsemblePredictor(
        cnn_path=f'{model_dir}/cnn_finetuned.h5',
        xgb_path=f'{model_dir}/xgboost_ensemble.json',
        temperature_path=f'{model_dir}/temperature_scalar.npz',
    )
    predictor.classify_all(catalogue_path)

    # Step 5: Assign confidence tiers
    df = pd.read_parquet(catalogue_path)
    df['confidence_tier'] = df['confidence_pc'].apply(assign_tiers)
    df.to_parquet(catalogue_path)
```

### Implementation Approach

**Input validation (D-17) — first thing Phase 2 does:**

```python
def validate_phase1_outputs(catalogue_path='data/catalogue/master.parquet'):
    """Validate Phase 1 outputs before starting Phase 2."""
    errors = []

    # 1. Catalogue exists
    if not Path(catalogue_path).exists():
        raise FileNotFoundError(f'Master catalogue not found: {catalogue_path}')

    df = pd.read_parquet(catalogue_path)

    # 2. Required columns
    REQUIRED = ['tic_id', 'tls_period', 'tls_t0', 'tls_sde', 'tls_snr',
                'tls_duration', 'tls_depth', 'preprocessed_path']
    missing = set(REQUIRED) - set(df.columns)
    if missing:
        errors.append(f'Missing columns: {missing}')

    # 3. SDE≥5 candidates exist
    if 'tls_sde' in df.columns:
        n_candidates = (df['tls_sde'] >= 5).sum()
        if n_candidates == 0:
            errors.append('No candidates with SDE >= 5')

    # 4. .npz files exist (sample check)
    if 'preprocessed_path' in df.columns:
        sample = df['preprocessed_path'].dropna().sample(min(10, len(df)))
        missing_files = [p for p in sample if not Path(p).exists()]
        if missing_files:
            errors.append(f'{len(missing_files)}/10 sampled .npz files missing')

    if errors:
        raise ValueError('Phase 1 validation failed:\n' + '\n'.join(f'  • {e}' for e in errors))
    print(f'✓ Phase 1 validated: {len(df)} rows, {n_candidates} candidates SDE≥5')
```

**Execution order during hackathon (after prep week pre-training):**

```
PREP WEEK (before hackathon):
  1. kepler_data_prep.py    → Download + fold Kepler DR24 TCEs
  2. train_kepler.py        → Pre-train CNN → kepler_pretrained.h5

HACKATHON DAY 1:
  3. Phase 1 executes       → Produces preprocessed LCs + master.parquet
  4. validate_phase1.py     → Confirms Phase 1 outputs are valid
  5. phase_folder.py        → Phase-fold all SDE≥5 candidates
  6. feature_extractor.py   → Extract 8+ features → append to Parquet
  7. centroid_analyzer.py   → TPF download + centroid for top 200 SDE≥7
  8. train_cnn_finetune.py  → Fine-tune on ExoFOP labels (2-3 hours)
  9. train_xgboost.py       → Train XGBoost on features (10 min)
  10. temperature_scaler.py → Learn T on calibration set (1 min)
  11. evaluate.py           → Full E1-E10 evaluation suite
  12. run_pipeline.py phase2 → Production inference on all candidates

HACKATHON DAY 2:
  13. Phase 3 starts        → Reads classified candidates from Parquet
```

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Phase 1 not complete when Phase 2 starts | Entire phase blocked | Validate first; have mock data for development/testing |
| Training takes longer than expected on T4 | Delays Phase 3 start | batch_size=32 + mixed precision; early stopping at patience=10 |
| Model files corrupted or incompatible | Inference fails silently | Shape verification after every model load (G5 guardrail) |
| Parquet schema drift between phases | Column mismatch errors | Schema contract document + validation function |

---

## Dependencies & Integration

### Execution Dependency Graph

```
kepler_pretrained.h5 (PREP WEEK)
         │
         ▼
Phase 1 outputs (master.parquet + .npz files)
         │
         ├──► validate_phase1_outputs()
         │
         ├──► PhaseFolder.run_all()  → data/folded/*.npz
         │         │
         │         ├──► FeatureExtractor.run_all() → features in Parquet
         │         │         │
         │         │         ├──► train_xgboost.py → xgboost_ensemble.json
         │         │         │
         │         ▼         ▼
         │    train_cnn_finetune.py → cnn_finetuned.h5
         │              │
         │              ▼
         │    TemperatureScaler.fit() → temperature_scalar.npz
         │              │
         │              ▼
         └──► EnsemblePredictor.classify_all() → classifications in Parquet
                        │
                        ▼
              evaluate.py → metrics, plots, pass/fail gate
                        │
                        ▼
              Phase 3 reads: Gold-tier candidates for MCMC
```

### Module File Structure

```
src/phase2/
├── __init__.py
├── validate_phase1.py       # D-17: Input validation
├── phase_folder.py          # D-08: PhaseFolder class
├── feature_extractor.py     # D-06: FeatureExtractor class
├── centroid_analyzer.py     # D-09: CentroidAnalyzer (TPF-based)
├── data_generator.py        # D-04: TransitDataGenerator (Sequence)
├── train_kepler.py          # D-01: Kepler pre-training (standalone)
├── train_cnn_finetune.py    # D-02: TESS fine-tuning (standalone)
├── train_xgboost.py         # D-03: XGBoost training (standalone)
├── temperature_scaler.py    # D-13: Temperature scaling
├── ensemble_predictor.py    # D-11: EnsemblePredictor class
├── evaluate.py              # Full evaluation suite (E1-E10)
└── pipeline_integration.py  # Hooks into run_pipeline.py
```

### Critical Path (Time-Constrained)

| Step | Duration | Parallelizable | Critical? |
|---|---|---|---|
| Phase-folding 60k candidates | ~30 min (GPU) | Yes (per-star) | Yes |
| Feature extraction | ~45 min (CPU+GPU) | Yes (per-star) | Yes |
| Centroid analysis (200 TPFs) | ~1 hour (network-bound) | Yes | No (can skip initially) |
| CNN fine-tuning | ~2-3 hours (T4) | No | Yes |
| XGBoost training | ~10 min (T4) | After features done | Yes |
| Temperature calibration | ~1 min | After both models | Yes |
| Evaluation suite | ~5 min | After calibration | Yes |
| **Total critical path** | **~4-5 hours** | | |

---

## RESEARCH COMPLETE
