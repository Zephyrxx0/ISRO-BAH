# Phase 01: Foundation — Research

**Researched:** 2026-06-28
**Focus:** Data ingestion, preprocessing, and TLS period search implementation

## 1. Lightkurve / Astroquery Bulk Download

### API & Usage

There is no single "download entire sector" call in lightkurve. The approach is:

1. **Get target list from MAST** — query all 2-min cadence observations for a sector
2. **Download individually** — iterate over TIC IDs and download PDCSAP light curves

```python
from astroquery.mast import Observations
import lightkurve as lk

# Step 1: Get all 2-min cadence observations for a sector
obs = Observations.query_criteria(
    obs_collection="TESS",
    dataproduct_type="timeseries",
    sequence_number=1,  # sector number
    t_exptime=[100, 130],  # 120s = 2-min cadence
)
# Extract unique TIC IDs from target_name column
tic_ids = list(set(obs['target_name']))

# Step 2: Download per star (in loop with error handling)
for tic_id in tic_ids:
    sr = lk.search_lightcurve(f"TIC {tic_id}", mission="TESS", sector=1, author="SPOC")
    if len(sr) > 0:
        lc = sr[0].download(quality_bitmask="hard", flux_column="pdcsap_flux")
        # Serialize to .npz
        np.savez_compressed(
            f"data/raw/sector1/TIC_{tic_id}_raw.npz",
            time=lc.time.value,
            flux=lc.flux.value,
            flux_err=lc.flux_err.value,
            quality=lc.quality.value,
            cadenceno=lc.cadenceno.value
        )
```

**Alternative bulk approach** (faster, avoids per-star MAST queries):
```python
from astroquery.mast import Observations

# Get all data products for the sector at once
obs = Observations.query_criteria(
    obs_collection="TESS", sequence_number=1,
    dataproduct_type="timeseries", t_exptime=[100, 130]
)
products = Observations.get_product_list(obs)
lc_products = Observations.filter_products(products, productSubGroupDescription="LC")
# Bulk download all FITS files
manifest = Observations.download_products(lc_products, download_dir="data/raw/sector1/")
# Then parse FITS → .npz in a separate step
```

### Gotchas & Edge Cases

- **Rate limiting**: MAST throttles at ~100 concurrent requests. Use exponential backoff + jitter (D-07, D-08). Sleep 0.5–2s between requests.
- **lightkurve caching**: lightkurve caches to `~/.lightkurve-cache/` by default. For bulk ops, use `download_dir` parameter or astroquery directly.
- **quality_bitmask options**: `"none"` (0), `"default"` (1130799), `"hard"` (1664431), `"hardest"` (2096639). Use `"hard"` for initial download, apply custom mask later.
- **Missing targets**: Some TIC IDs have no SPOC light curve (only FFI). Skip and log.
- **PDCSAP vs SAP**: Always use PDCSAP (Pre-search Data Conditioning) — it removes instrumental systematics while preserving transit signals.
- **Sector overlap**: Some stars appear in multiple sectors. Download each sector separately per D-06.

### Performance Notes

- **Targets per sector**: ~20,000 stars per sector at 2-min cadence (Sectors 1–3 era). Total ~60k across 3 sectors.
- **File size per LC**: ~2 MB FITS, compresses to ~200–400 KB as .npz (float32 time/flux/flux_err + int32 quality).
- **Total disk**: ~60k × 0.3 MB = ~18 GB raw .npz. With FITS cache: ~120 GB total.
- **Download time**: At ~1 LC/sec with rate limiting: ~60k / 3600 = ~17 hours total. **Must pre-download during prep week (D-05).**
- **Bulk download via astroquery**: Can download all FITS for a sector in one batch (faster than per-star lightkurve calls).

### Downstream Impact

- Phase 2 needs `.npz` files with consistent arrays: `time`, `flux`, `flux_err`, `quality`.
- Phase 2's CNN expects phase-folded views derived from these preprocessed light curves.
- The Parquet master catalogue must include: TIC ID, sector, RA, Dec, Tmag, Teff, logg, radius, mass, CROWDSAP — queried from TICv8 during ingestion.

---

## 2. Wotan Biweight Detrending

### API & Usage

```python
from wotan import flatten

# Basic biweight detrending
flatten_flux, trend = flatten(
    time,                    # array of times (days)
    flux,                    # array of normalized flux
    method='biweight',       # Tukey's biweight (bisquare)
    window_length=0.75,      # days — MINIMUM per PREP-03
    break_tolerance=0.5,     # treat gaps > 0.5 days as segment breaks
    return_trend=True,
    cval=5.0                 # biweight tuning parameter (default 5.0)
)
```

**Key parameters:**
- `window_length`: In days. Must be ≥ 0.75d per requirement. Optimal is ~3× transit duration (from Hippke 2019 paper). For typical hot Jupiters (T14 ~ 2–3h), 0.75d works. For longer-period planets (T14 ~ 6h), use 1.0–1.5d.
- `break_tolerance`: Automatically segments data at gaps larger than this value. Critical for TESS 13-day gaps.
- `cval`: Tukey's biweight tuning constant. Default 5.0 gives ~95% efficiency. Paper recommends c≈5 as optimal.
- `method='biweight'`: Uses iterative Newton-Raphson convergence (not one-step estimate).

**Transit-preserving detrending:**
```python
# If transit ephemeris is known (for validation targets), mask in-transit points
from wotan import flatten
from transitleastsquares import transit_mask

# Create mask for known transit
in_transit = transit_mask(time, period=1.2749, duration=0.12, T0=epoch)
flatten_flux, trend = flatten(
    time, flux,
    method='biweight',
    window_length=0.75,
    break_tolerance=0.5,
    mask=in_transit  # wotan's mask parameter excludes these from trend calc
)
```

### Gotchas & Edge Cases

- **Window too short**: If window_length < 2.2 × T14, transit depth is reduced by >2%. At 0.75d, safe for transits up to ~8 hours duration.
- **WASP-121b validation**: T14 ≈ 2.88 hours, window 0.75d = 18 hours = 6.25× T14. Safe — preserves >99% of transit depth.
- **Edge effects**: Biweight with `break_tolerance` handles TESS gaps well. Points within half-window of edges use shrinking window (best practice per Hippke 2019).
- **Shallow transits (50–200 ppm)**: Biweight is robust to in-transit points pulling the trend. The c=5 tuning means points >5 MADs from local median get zero weight — transit dips (typically 3–10 MAD) are partially down-weighted but not zeroed.
- **Computational cost**: ~0.1s per star (biweight with numba JIT). 60k stars = ~100 minutes single-threaded.
- **NaN handling**: Wotan handles NaN values gracefully — they are excluded from window calculations.
- **Normalization first**: Flux MUST be normalized (median=1.0) before detrending (PREP-02).

### Performance Notes

- Biweight with numba: ~0.05–0.1s per LC (20,000 points)
- 60k stars single-threaded: ~100 min
- With 4-core multiprocessing: ~25 min
- Memory: negligible (processes one LC at a time)

### Downstream Impact

- Phase 2 CNN training requires properly detrended LCs that preserve transit morphology.
- ADR-0003's synthetic transit injection (50–200 ppm) depends on detrending NOT erasing these shallow signals.
- GP detrending (PREP-04) runs AFTER TLS detection on top 100 candidates only — biweight is the bulk workhorse.


---

## 3. Transit Least Squares (TLS)

### API & Usage

```python
from transitleastsquares import transitleastsquares, transit_mask, catalog_info

# Get stellar parameters for TLS (limb darkening, density priors)
ab, mass, mass_min, mass_max, radius, radius_min, radius_max = catalog_info(TIC_ID=259377017)

# Run TLS
model = transitleastsquares(time, flux)
results = model.power(
    period_min=0.5,           # days
    period_max=30.0,          # days
    n_transits_min=2,         # minimum transits required
    oversampling_factor=5,    # oversample period grid (default 3)
    duration_grid_step=1.05,  # 5% steps in duration grid
    use_threads=1,            # single-threaded (we parallelize at star level)
    # Stellar priors (improves speed + accuracy)
    R_star=radius,
    R_star_min=radius_min,
    R_star_max=radius_max,
    M_star=mass,
    M_star_min=mass_min,
    M_star_max=mass_max,
    u=ab,                     # quadratic limb darkening [u1, u2]
)
```

**Key output fields:**
```python
results.period                # best-fit period (days)
results.T0                    # mid-transit epoch (BJD)
results.duration              # transit duration (days)
results.depth                 # transit depth (fraction, e.g., 0.01 = 1%)
results.SDE                   # Signal Detection Efficiency
results.snr                   # Signal-to-noise ratio (white noise)
results.snr_pink_per_transit  # SNR accounting for correlated noise
results.FAP                   # False Alarm Probability
results.rp_rs                 # Rp/Rs ratio
results.transit_times         # individual transit mid-times
results.in_transit            # boolean mask of in-transit points
results.power                 # full SDE periodogram array
results.periods               # corresponding period array
results.odd_even_mismatch     # significance of odd/even depth difference
results.distinct_transit_count  # number of distinct transits observed
```

**Multi-planet iterative search (DET-03):**
```python
results_list = []
time_masked, flux_masked = time.copy(), flux.copy()

for iteration in range(3):  # 3 iterations per star
    model = transitleastsquares(time_masked, flux_masked)
    results = model.power(period_min=0.5, period_max=30.0, n_transits_min=2)
    
    if results.SDE < 5.0:  # Below detection threshold
        break
    
    results_list.append(results)
    
    # Mask found transit and re-search
    intransit = transit_mask(
        time_masked,
        results.period,
        results.duration,
        results.T0
    )
    # Remove in-transit points for next iteration
    time_masked = time_masked[~intransit]
    flux_masked = flux_masked[~intransit]
```

**Period grid calculation:**
- TLS uses Ofir (2014) optimal frequency grid internally
- For 27-day TESS sector, period_min=0.5d, period_max=30d → ~10,000–15,000 trial periods
- With oversampling_factor=5: ~50,000–75,000 periods (matches our 50k requirement)
- `n_transits_min=2` is critical — with 27-day sector, max detectable period ≈ 13.5d (2 transits). With 3 sectors stitched: up to 40d.

### Gotchas & Edge Cases

- **Single-sector limitation**: 27-day baseline means only 2 transits for P ≈ 13d. SDE will be lower. Consider stitching sectors for long-period search.
- **Computation time**: ~10s per K2 LC (80 days, 4000 points). TESS 2-min for 27 days = ~19,000 points → ~30–60s per star without priors, ~10–20s with stellar density priors.
- **Memory**: TLS is memory-efficient but CPU-intensive. Each star is independent → perfect for multiprocessing.
- **Transit template**: TLS uses Mandel & Agol transit model (not a box). Requires limb darkening coefficients — use `catalog_info` or provide manually from TICv8.
- **FAP vs SDE**: FAP is computationally expensive (bootstrap). Use SDE thresholds (our 3-tier system) instead of FAP for bulk processing.
- **Edge transits**: Partial transits near data gaps reduce SDE. TLS handles this but reports lower `distinct_transit_count`.
- **Harmonic contamination**: EBs at period P produce TLS peaks at P/2, P/3. Multi-planet search helps disambiguate.
- **foldedleastsquares**: Note that `transitleastsquares` package was recently renamed/forked to `foldedleastsquares` on PyPI. Check which version is current.

### Performance Notes

- **Per-star time**: 10–60s depending on data length, period range, oversampling
- **60k stars**: At 30s average × 60k = 500 hours single-threaded. With 4 cores: ~125 hours. With 8 cores (Colab): ~63 hours.
- **Optimization**: Use stellar density priors to constrain duration grid. Set `duration_grid_step=1.1` for first pass (faster), `1.05` for validation targets.
- **Checkpoint strategy**: Write TLS results per star immediately. Resume by checking which .npz files exist in `data/tls/sector{N}/`.
- **CDPP computation**: Not built into TLS. Calculate separately: `cdpp = np.std(flux_binned_1hr) * 1e6` (ppm).

### Downstream Impact

- TLS SDE values gate Phase 2: SDE ≥ 7 → full pipeline, 5 ≤ SDE < 7 → sub-threshold archive.
- TLS `results.period` and `results.T0` are used in Phase 2 for phase-folding into 2001-point global + 201-point local views.
- `results.in_transit` mask is used for feature extraction (odd/even depth, centroid analysis).
- Multi-planet results expand the candidate catalogue significantly (3× potential candidates).

---

## 4. BLS Validation

### API & Usage

```python
from astropy.timeseries import BoxLeastSquares
import astropy.units as u

# Create BLS model
bls = BoxLeastSquares(time * u.day, flux, dy=flux_err)

# Compute BLS periodogram at TLS-detected period ± 5%
periods = np.linspace(tls_period * 0.95, tls_period * 1.05, 1000) * u.day
durations = np.linspace(0.01, 0.2, 20) * u.day  # trial durations

periodogram = bls.power(periods, durations, objective="snr")

# Get best parameters
best_idx = np.argmax(periodogram.power)
bls_period = periodogram.period[best_idx]
bls_depth = periodogram.depth[best_idx]
bls_duration = periodogram.duration[best_idx]
bls_t0 = periodogram.transit_time[best_idx]

# Compute statistics for validation
stats = bls.compute_stats(bls_period, bls_duration, bls_t0)
# stats keys: depth, depth_err, duration, transit_time, depth_odd, depth_even, etc.
```

**Cross-validation logic (DET-02):**
```python
def validate_with_bls(time, flux, flux_err, tls_period, tls_duration, tls_t0):
    """BLS validation of TLS detection. Returns True if confirmed."""
    bls = BoxLeastSquares(time * u.day, flux, dy=flux_err)
    
    # Narrow search around TLS period
    periods = np.linspace(tls_period * 0.98, tls_period * 1.02, 500) * u.day
    durations = [tls_duration * 0.5, tls_duration, tls_duration * 1.5] * u.day
    
    result = bls.power(periods, durations, objective="snr")
    best_power = np.max(result.power)
    best_period = result.period[np.argmax(result.power)].value
    
    # Validation criteria:
    # 1. BLS finds signal near TLS period (within 1%)
    period_match = abs(best_period - tls_period) / tls_period < 0.01
    # 2. BLS SNR > 6 (meaningful detection)
    snr_ok = best_power > 6.0
    
    return period_match and snr_ok, best_power
```

### Gotchas & Edge Cases

- **BLS vs TLS sensitivity**: BLS uses box model (no limb darkening). Expect 10–15% lower SDE for small planets. Good for cross-validation — if BLS also finds it, signal is robust.
- **Duration grid**: Must include plausible transit durations. Too narrow misses signal; too wide wastes compute.
- **autopower vs power**: `autopower(duration)` automatically determines period grid. Use `power(periods, durations)` for targeted validation around TLS period.
- **Objective**: Use `"snr"` objective for validation (more robust to correlated noise than log-likelihood).

### Performance Notes

- BLS is fast: ~0.5–2s per star for narrow period search
- Only runs on SDE ≥ 7 candidates (~100–500 stars): negligible total time
- Astropy C implementation is well-optimized

### Downstream Impact

- BLS confirmation adds confidence to TLS detections before Phase 2 classification.
- BLS `depth_odd` / `depth_even` from `compute_stats` feeds directly into Phase 2's odd/even feature (FEAT-01).
- Failed BLS validation on a TLS detection flags it as potentially spurious (useful metadata for classifier).


---

## 5. Celerite2 GP Detrending (PREP-04)

### API & Usage

```python
import numpy as np
from celerite2 import GaussianProcess
from celerite2.terms import Matern32Term
from scipy.optimize import minimize

# Matérn-3/2 kernel for correlated noise modeling
# sigma = amplitude of GP variability
# rho = correlation timescale (days)
kernel = Matern32Term(sigma=1e-3, rho=0.5)

# Build GP
gp = GaussianProcess(kernel, mean=1.0)
gp.compute(time, yerr=flux_err)  # time must be sorted ascending

# Log-likelihood for optimization
def neg_log_likelihood(params):
    sigma, rho = np.exp(params)
    gp.kernel = Matern32Term(sigma=sigma, rho=rho)
    gp.recompute()
    return -gp.log_likelihood(flux)

# Optimize hyperparameters
x0 = np.log([1e-3, 0.5])  # initial: sigma=1e-3, rho=0.5 days
result = minimize(neg_log_likelihood, x0, method="Nelder-Mead")
sigma_opt, rho_opt = np.exp(result.x)

# Predict GP trend (mask transits first!)
gp.kernel = Matern32Term(sigma=sigma_opt, rho=rho_opt)
gp.recompute()
mu, var = gp.predict(flux, t=time, return_var=True)
gp_detrended_flux = flux / mu  # divide out the trend
```

**With transit masking (critical for top candidates):**
```python
# Mask in-transit points before GP fitting
from transitleastsquares import transit_mask

mask = transit_mask(time, period=tls_period, duration=tls_duration, T0=tls_T0)
time_oot = time[~mask]
flux_oot = flux[~mask]
flux_err_oot = flux_err[~mask]

# Fit GP only on out-of-transit data
gp.compute(time_oot, yerr=flux_err_oot)
# ... optimize ...

# Predict on ALL time points (including in-transit)
mu_all = gp.predict(flux_oot, t=time, return_var=False)
gp_detrended = flux / mu_all
```

### Gotchas & Edge Cases

- **Only top 100 candidates** (PREP-04): GP is expensive. Don't run on all 60k stars.
- **Transit masking is essential**: GP will fit transits as noise if not masked. Use TLS-detected ephemeris.
- **Matérn-3/2 parameters**: 
  - `sigma`: ~100–10000 ppm typical for TESS stars (1e-4 to 1e-2 in normalized flux)
  - `rho`: correlation timescale. Typical 0.3–2 days for stellar variability. Should be > transit duration.
- **Numerical stability**: `eps=0.01` parameter in Matern32Term controls approximation quality. Default is fine.
- **Time sorting**: celerite2 requires strictly sorted time arrays. TESS data is already sorted.
- **Scalability**: celerite2 is O(N) — designed for large datasets. 20k points per LC is fine.
- **Mean function**: Set `mean=1.0` for normalized flux (not 0.0).

### Performance Notes

- celerite2 GP computation: O(N) where N = number of data points
- ~0.5–2s per star including hyperparameter optimization
- Top 100 candidates: ~100–200s total — negligible
- Memory: minimal (celerite2 is memory-efficient)

### Downstream Impact

- GP-detrended light curves provide cleaner phase-folded views for CNN (Phase 2).
- GP residual variance provides a noise estimate for Phase 3 MCMC.
- GP hyperparameters (sigma, rho) could be useful features for Phase 2 XGBoost classifier.

---

## 6. Data Volumes & Performance

### Estimated Data Sizes

| Item | Per Star | Per Sector (~20k) | Total (3 sectors, ~60k) |
|------|----------|-------------------|-------------------------|
| Raw FITS (from MAST) | ~2 MB | ~40 GB | ~120 GB |
| Raw .npz (compressed) | ~300 KB | ~6 GB | ~18 GB |
| Preprocessed .npz | ~250 KB | ~5 GB | ~15 GB |
| TLS results .npz | ~50 KB | ~1 GB | ~3 GB |
| Per-sector Parquet | — | ~5 MB | ~15 MB |
| Master Parquet catalogue | — | — | ~20 MB |
| **Total disk footprint** | — | — | **~36 GB** (without FITS cache) |

### Light Curve Dimensions

- TESS 2-min cadence, 27-day sector: ~19,440 cadences per star (27 × 24 × 60 / 2)
- After quality masking: ~17,000–18,000 valid points typical
- 13-day data gap removes ~9,360 cadences → orbit 1 has ~9,000, orbit 2 has ~9,000
- Float32 arrays: time(4B) + flux(4B) + flux_err(4B) + quality(4B) = 16 bytes/cadence
- Per star raw: ~310 KB uncompressed, ~200–400 KB compressed (.npz)

### Memory Requirements

- **Per-process memory**: ~100–200 MB (one LC loaded + TLS working memory)
- **Multiprocessing**: 4 workers × 200 MB = ~800 MB. Colab free tier has 12 GB RAM → safe with 8 workers.
- **Parquet operations**: pandas DataFrame of 60k rows × 30 columns ≈ 50 MB. Trivial.
- **No need to hold all LCs in memory** — process one at a time, write results immediately.

### Multiprocessing Strategy (D-02)

```python
from multiprocessing import Pool
from functools import partial

def process_star(tic_id, sector, config):
    """Process one star: preprocess + TLS. Returns result dict or None on failure."""
    try:
        # Load
        data = np.load(f"data/raw/sector{sector}/TIC_{tic_id}_raw.npz")
        # Preprocess
        preprocessed = preprocess(data, config)
        # TLS
        tls_result = run_tls(preprocessed, config)
        # Save
        save_results(tic_id, sector, preprocessed, tls_result)
        return {"tic_id": tic_id, "status": "success", "sde": tls_result.SDE}
    except Exception as e:
        return {"tic_id": tic_id, "status": "failed", "error": str(e)}

# Per-sector batching with multiprocessing within sector
for sector in [1, 2, 3]:
    tic_ids = get_sector_tics(sector)
    with Pool(processes=4) as pool:
        results = list(tqdm(
            pool.imap(partial(process_star, sector=sector, config=config), tic_ids),
            total=len(tic_ids)
        ))
```

### Timing Estimates

| Stage | Per Star | 60k Stars (4 cores) | Notes |
|-------|----------|---------------------|-------|
| Download (pre-hackathon) | ~1s | ~17h | Rate-limited by MAST |
| Load .npz | ~5ms | ~5 min | I/O bound |
| Quality masking + sigma clip | ~10ms | ~10 min | Trivial |
| Normalization | ~1ms | ~1 min | Trivial |
| Biweight detrending | ~100ms | ~25 min | Numba-accelerated |
| TLS search (with priors) | ~20s | ~83 hours | **Dominant cost** |
| BLS validation (SDE≥7 only) | ~1s | ~10 min | ~500 candidates |
| **Total pipeline** | ~20s | **~85 hours** | Per-sector: ~28h |

**Critical insight**: TLS is the bottleneck. Strategies to manage:
1. Use stellar density priors (reduces search space by 3–10×)
2. Use `duration_grid_step=1.1` (not 1.05) for bulk pass
3. Colab instances with 2 vCPUs = ~2 concurrent TLS. Run overnight.
4. Checkpoint per star — resume after Colab disconnect (D-04)


---

## 7. TESS Data Gaps & Quality Flags

### Data Gap Structure

TESS observes in ~27-day sectors, split into two ~13.5-day "orbits" by a perigee passage (data downlink):
- **Orbit 1**: Days 0–13.5 (approximately)
- **Data gap**: Days 13.5–14.0 (perigee passage, ~0.5–1 day)
- **Orbit 2**: Days 14.0–27.5 (approximately)

The gap is NOT exactly 13 days — it varies by sector. Actual gap is typically 0.5–1.5 days of no data.

### Quality Flag Bitmask (TESS SPOC)

The `QUALITY` column in TESS FITS files uses a 32-bit integer bitmask. Key flags to mask (PREP-01):

| Bit | Value | Name | Description | Action |
|-----|-------|------|-------------|--------|
| 0 | 1 | AttitudeTweak | Spacecraft attitude tweaked | **MASK** |
| 1 | 2 | SafeMode | Spacecraft in safe mode | **MASK** |
| 2 | 4 | CoarsePoint | Spacecraft in coarse point | **MASK** |
| 3 | 8 | EarthPoint | Spacecraft in Earth point | **MASK** |
| 4 | 16 | Argabrightening | Argabrightening event | **MASK** |
| 5 | 32 | Desat | Reaction wheel desaturation | Consider masking |
| 6 | 64 | ApertureCosmic | Cosmic ray in optimal aperture | **MASK** |
| 7 | 128 | ManualExclude | Manual exclude | **MASK** |
| 8 | 256 | SensitivityDropout | Sensitivity dropout | MASK |
| 9 | 512 | ImpulsiveOutlier | Impulsive outlier removed | MASK |
| 10 | 1024 | CollateralCosmic | Cosmic ray in collateral data | Consider |
| 11 | 2048 | Straylight | Straylight detected | Consider |

**Recommended bitmask for our pipeline:**
```python
# PREP-01: Remove AttitudeTweak, SafeMode, CosmicRay, ManualExclude
# Plus CoarsePoint, EarthPoint, Argabrightening, SensitivityDropout, ImpulsiveOutlier
QUALITY_BITMASK = (
    1 |    # AttitudeTweak
    2 |    # SafeMode
    4 |    # CoarsePoint
    8 |    # EarthPoint
    16 |   # Argabrightening
    64 |   # ApertureCosmic (CosmicRay in aperture)
    128 |  # ManualExclude
    256 |  # SensitivityDropout
    512    # ImpulsiveOutlier
)  # = 991

# Apply mask
quality_mask = (quality & QUALITY_BITMASK) == 0  # True = good cadence
time_clean = time[quality_mask]
flux_clean = flux[quality_mask]
```

**Lightkurve preset values:**
- `"default"` = 1130799 (masks most flags including straylight)
- `"hard"` = 1664431 (stricter, masks desat events)
- `"hardest"` = 2096639 (most aggressive)

### Gap Handling (PREP-05)

```python
# MASK gaps, do NOT interpolate
# Identify gap edges — cadences immediately before/after gaps
dt = np.diff(time_clean)
median_cadence = np.median(dt)  # ~2 min = 0.00139 days
gap_threshold = 0.5  # days — any gap > 0.5d is a "data gap"
gap_indices = np.where(dt > gap_threshold)[0]

# Flag gap-edge cadences as unreliable (±2 cadences around gaps)
gap_edge_mask = np.ones(len(time_clean), dtype=bool)
for idx in gap_indices:
    gap_edge_mask[max(0, idx-1):idx+1] = False      # before gap
    gap_edge_mask[idx+1:min(len(time_clean), idx+3)] = False  # after gap

# For wotan: use break_tolerance parameter
flatten_flux, trend = flatten(
    time_clean, flux_clean,
    method='biweight',
    window_length=0.75,
    break_tolerance=0.5  # segments at gaps > 0.5d
)
```

### Gotchas & Edge Cases

- **13-day gap varies**: Don't hard-code 13 days. Detect gaps dynamically from time array.
- **Momentum dumps**: Short gaps (~30 min) every ~2.5 days from reaction wheel desats. Usually bit 5 (value 32). We mask these.
- **Scattered light**: Near orbit start/end, Earth/Moon can scatter light into detector. Bit 11 (value 2048). Consider masking first/last ~0.5 days of each orbit.
- **< 500 cadences filter** (PREP-06): After quality masking, some stars have very few valid points. Exclude these.

### Downstream Impact

- Gap handling affects TLS sensitivity — fewer transits observable means lower SDE.
- `break_tolerance=0.5` in wotan ensures detrending doesn't bridge the 13-day gap.
- Phase 2's CNN input must handle variable-length light curves (phase-folding normalizes this).

---

## 8. TICv8 Limb Darkening (PREP-07)

### API & Usage

TICv8 does NOT directly provide limb darkening coefficients. The workflow is:

1. **Query stellar parameters from TICv8** (Teff, logg, [Fe/H])
2. **Interpolate limb darkening tables** (Claret 2017 or Claret & Bloemen 2011)

```python
from astroquery.mast import Catalogs
import numpy as np

# Step 1: Query TICv8 for stellar parameters
tic_data = Catalogs.query_object(f"TIC {tic_id}", catalog="TIC")
teff = tic_data['Teff'][0]     # Effective temperature (K)
logg = tic_data['logg'][0]     # Surface gravity
met = tic_data['MH'][0]        # Metallicity [M/H]
# Also get: RA, Dec, Tmag, rad, mass, CROWDSAP, etc.

# Step 2: Interpolate LD coefficients from pre-loaded table
# Claret (2017) A&A 600, A30 — quadratic LD for TESS bandpass
# Table available from VizieR: J/A+A/600/A30
def get_quadratic_ld(teff, logg, met, ld_table):
    """Interpolate quadratic limb darkening [u1, u2] for TESS bandpass."""
    from scipy.interpolate import LinearNDInterpolator
    
    points = np.column_stack([ld_table['Teff'], ld_table['logg'], ld_table['MH']])
    u1_interp = LinearNDInterpolator(points, ld_table['u1'])
    u2_interp = LinearNDInterpolator(points, ld_table['u2'])
    
    u1 = float(u1_interp(teff, logg, met))
    u2 = float(u2_interp(teff, logg, met))
    return [u1, u2]
```

**Pre-loading the Claret table:**
```python
# Download once from VizieR during prep week
from astroquery.vizier import Vizier

# Claret (2017) TESS limb darkening coefficients
# Catalog: J/A+A/600/A30 (Table 5 — quadratic law, TESS filter)
v = Vizier(columns=['Teff', 'logg', 'Z', 'u1', 'u2'])
tables = v.get_catalogs('J/A+A/600/A30')
ld_table = tables[0]  # quadratic law coefficients for TESS
ld_table.write('data/reference/claret2017_tess_ld.csv', format='csv')
```

**Alternative — TLS built-in catalog_info:**
```python
from transitleastsquares import catalog_info

# Returns LD coefficients along with mass/radius from TIC
ab, mass, mass_min, mass_max, radius, radius_min, radius_max = catalog_info(TIC_ID=tic_id)
# ab = [u1, u2] quadratic limb darkening for Kepler bandpass
# NOTE: TLS catalog_info uses Kepler bandpass by default, NOT TESS!
```

### Gotchas & Edge Cases

- **TLS `catalog_info` uses Kepler bandpass**, not TESS. For TESS data, we MUST use Claret (2017) TESS-specific tables or Claret (2018) updated tables.
- **Missing parameters**: ~5–10% of TIC targets lack Teff or logg. Fallback: use default solar LD [0.4, 0.26] for these stars (flag in log).
- **Metallicity**: TICv8 metallicity is often NaN. Use solar [M/H]=0.0 as default for interpolation.
- **Table boundaries**: Claret tables cover Teff 3500–50000K, logg 0.0–5.0. Cool M-dwarfs near edge may extrapolate poorly.
- **Quadratic vs power-2 law**: Quadratic [u1, u2] is standard for batman. Power-2 law is newer but less supported.
- **Batch query**: Query TICv8 in batches using `Catalogs.query_criteria` with TIC ID list for efficiency.

### Performance Notes

- TICv8 query: ~0.5s per star (MAST API). Batch query 1000 at a time: ~10s per batch.
- LD interpolation: ~1ms per star (pre-loaded table). Negligible.
- Pre-download all stellar parameters during prep week and store in master Parquet.

### Downstream Impact

- Per-star LD coefficients are used by:
  - TLS (transit template fitting)
  - batman (Phase 3 Mandel-Agol model fitting)
  - MCMC (Phase 3 parameter estimation)
- Correct LD avoids systematic bias in transit depth estimates (can be 5–15% error with wrong LD).
- Store [u1, u2] per star in master Parquet catalogue for downstream phases.


---

## 9. Known Validation Targets

### WASP-121b (Sector 1) — VAL-01

| Parameter | Value | Source |
|-----------|-------|--------|
| TIC ID | 22529346 | ExoFOP |
| Period | 1.2749255 ± 0.0000003 days | Delrez+ 2016 |
| Transit depth | ~15,400 ppm (1.54%) | Hot Jupiter, Rp=1.75 Rj |
| Duration T14 | ~2.88 hours (0.12 days) | |
| Epoch T0 (BJD) | 2456635.70832 | |
| Sector | 1 | Primary mission |
| Rp/Rs | ~0.124 | |
| Expected SDE | > 50 (very strong) | Deep transit, short period |

**Why it's useful**: Ultra-hot Jupiter with deep, unmistakable transit. If pipeline can't find WASP-121b, something is fundamentally broken. Serves as Day 1 sanity check.

### TOI-270 (Sector 3) — VAL-02

| Parameter | TOI-270 b | TOI-270 c | TOI-270 d |
|-----------|-----------|-----------|-----------|
| TIC ID | 259377017 | 259377017 | 259377017 |
| Period (days) | 3.360 | 5.660 | 11.380 |
| Depth (ppm) | ~1,730 | ~2,770 | ~2,280 |
| Duration (hours) | ~1.3 | ~1.6 | ~2.1 |
| Rp (R⊕) | 1.25 | 2.42 | 2.13 |
| Sector | 3, 4, 5+ | 3, 4, 5+ | 3, 4, 5+ |
| Expected SDE | > 15 | > 20 | > 10 |

**Why it's useful**: Three planets in near-resonance (5:3 and 2:1 period ratios). Tests multi-planet iterative search. All three detectable in single sector. M dwarf host (quiet star, low noise).

**Multi-planet search expectation**: 
- Iteration 1: Finds planet c (highest SDE due to deepest transit × most transits in sector)
- Iteration 2: Finds planet b (short period, many transits)
- Iteration 3: Finds planet d (only 2–3 transits in sector 3, lower SDE)

### L 98-59 (Sector 2) — VAL-02

| Parameter | L 98-59 b | L 98-59 c | L 98-59 d |
|-----------|-----------|-----------|-----------|
| TIC ID | 307210830 | 307210830 | 307210830 |
| Period (days) | 2.2531 | 3.6904 | 7.4512 |
| Depth (ppm) | ~400 | ~1,170 | ~1,580 |
| Duration (hours) | ~0.9 | ~1.1 | ~1.5 |
| Rp (R⊕) | 0.80 | 1.35 | 1.57 |
| Sector | 2, 5, 8+ | 2, 5, 8+ | 2, 5, 8+ |
| Expected SDE | ~7–10 | > 15 | > 10 |

**Why it's useful**: Tests detection of Earth-sized planet (b is only 0.8 R⊕ with ~400 ppm depth). This is near our detection limit. M3 dwarf at 10.6 pc. Validates shallow transit preservation.

**Critical test**: L 98-59 b at 400 ppm is the hardest target. If biweight detrending at 0.75d preserves this signal and TLS detects it with SDE ≥ 5, our pipeline handles shallow transits.

### Validation Test Matrix

| Target | Sector | Test | Pass Criterion |
|--------|--------|------|----------------|
| WASP-121b | 1 | Basic detection | SDE > 30, period within 0.01% |
| TOI-270 b,c,d | 3 | Multi-planet iterative | All 3 found with SDE ≥ 5 |
| L 98-59 b,c,d | 2 | Shallow transit + multi-planet | c,d found SDE ≥ 7; b found SDE ≥ 5 |
| WASP-121b post-detrend | 1 | Detrending preservation | SDE after detrend ≥ 90% of SDE before |

---

## 10. Parquet Schema Design

### Master Catalogue (`data/catalogue/master.parquet`)

```python
import pyarrow as pa

master_schema = pa.schema([
    # Identifiers
    ('tic_id', pa.int64()),
    ('sector', pa.int8()),
    
    # Coordinates
    ('ra', pa.float64()),          # degrees
    ('dec', pa.float64()),         # degrees
    
    # Stellar parameters (from TICv8)
    ('tmag', pa.float32()),        # TESS magnitude
    ('teff', pa.float32()),        # Effective temperature (K)
    ('logg', pa.float32()),        # Surface gravity
    ('radius', pa.float32()),      # Stellar radius (R_sun)
    ('mass', pa.float32()),        # Stellar mass (M_sun)
    ('metallicity', pa.float32()), # [M/H]
    ('crowdsap', pa.float32()),    # Contamination ratio
    
    # Limb darkening
    ('ld_u1', pa.float32()),       # Quadratic LD coefficient 1
    ('ld_u2', pa.float32()),       # Quadratic LD coefficient 2
    
    # Data quality
    ('n_cadences_raw', pa.int32()),     # Total cadences in sector
    ('n_cadences_valid', pa.int32()),   # After quality masking
    ('cdpp_1hr', pa.float32()),         # 1-hour CDPP (ppm)
    
    # Processing status
    ('preprocess_status', pa.string()), # "success" | "failed" | "excluded"
    ('exclude_reason', pa.string()),    # "tmag<6" | "cadences<500" | null
    
    # Timing
    ('download_s', pa.float32()),     # Download time (seconds)
    ('preprocess_s', pa.float32()),   # Preprocessing time
    ('tls_s', pa.float32()),          # TLS search time
])
```

### TLS Results Table (`data/catalogue/tls_results.parquet`)

```python
tls_schema = pa.schema([
    # Identifiers
    ('tic_id', pa.int64()),
    ('sector', pa.int8()),
    ('iteration', pa.int8()),      # 1, 2, or 3 (multi-planet search)
    
    # Detection
    ('period', pa.float64()),       # Best-fit period (days)
    ('period_err', pa.float64()),   # Period uncertainty (days)
    ('t0', pa.float64()),           # Mid-transit epoch (BJD-2457000)
    ('duration', pa.float32()),     # Transit duration (days)
    ('depth', pa.float32()),        # Transit depth (fraction)
    ('depth_ppm', pa.float32()),    # Transit depth (ppm)
    ('rp_rs', pa.float32()),        # Planet-to-star radius ratio
    
    # Detection metrics
    ('sde', pa.float32()),          # Signal Detection Efficiency
    ('snr', pa.float32()),          # Signal-to-noise ratio
    ('snr_pink', pa.float32()),     # SNR with pink noise correction
    ('cdpp', pa.float32()),         # CDPP at transit timescale (ppm)
    ('fap', pa.float64()),          # False alarm probability (if computed)
    
    # Transit statistics
    ('n_transits', pa.int16()),              # Distinct transits observed
    ('odd_even_mismatch', pa.float32()),     # Odd/even depth sigma
    
    # SDE gating
    ('sde_tier', pa.string()),      # "full" (≥7) | "subthreshold" (5-7) | "discard" (<5)
    
    # BLS validation (DET-02)
    ('bls_confirmed', pa.bool_()),  # BLS cross-validation result
    ('bls_snr', pa.float32()),      # BLS SNR at TLS period
    ('bls_period', pa.float64()),   # BLS best period
    
    # Multi-planet linking
    ('planet_index', pa.int8()),    # 0-indexed planet number for this star
])
```

### Per-Sector Parquet (`data/catalogue/sector_{N}.parquet`)

Same schema as master catalogue but filtered to one sector. Enables quick per-sector queries.

### Design Decisions

- **int64 for TIC ID**: TIC IDs can exceed 2^31. Use int64.
- **float32 for most values**: Sufficient precision, halves storage vs float64.
- **float64 for period/epoch**: Need high precision for phase-folding.
- **String for status columns**: Readable, filterable, no enum encoding needed at this scale.
- **Separate TLS results table**: One star can have multiple signals (multi-planet). Master catalogue is one-row-per-star-per-sector.
- **Partitioning**: By sector (simple, matches directory structure). No need for complex partitioning at 60k rows.

### Usage Patterns

```python
import pandas as pd

# Load master catalogue
master = pd.read_parquet("data/catalogue/master.parquet")

# Get all SDE ≥ 7 candidates
tls = pd.read_parquet("data/catalogue/tls_results.parquet")
full_pipeline = tls[tls['sde_tier'] == 'full']

# Join for Phase 2 input
candidates = full_pipeline.merge(master, on=['tic_id', 'sector'])

# Filter: CROWDSAP < 0.5 blocks PC classification (FEAT-03)
clean_candidates = candidates[candidates['crowdsap'] < 0.5]
```


---

## Implementation Risks

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|------------|
| **TLS runtime exceeds prep window** | HIGH | MEDIUM | Use stellar density priors, `duration_grid_step=1.1`, checkpoint per star. If needed, reduce to sectors 1+2 for TLS, sector 3 as stretch. |
| **MAST rate limiting during download** | HIGH | HIGH | Pre-download ALL data during prep week (D-05). Exponential backoff + jitter (D-07, D-08). Use bulk astroquery, not per-star lightkurve. |
| **Colab disconnects mid-processing** | MEDIUM | HIGH | File-based checkpoints (D-04). Each star writes result immediately. Resume = skip existing files. |
| **Biweight removes shallow transits** | MEDIUM | LOW | Window 0.75d is safe for T14 < 8h. Validate on WASP-121b AND L 98-59 b (400 ppm). If L 98-59 b fails, increase window to 1.0d. |
| **TLS fails on multi-planet systems** | MEDIUM | LOW | Validated approach (TRAPPIST-1 recovery in Hippke 2019). Use `transit_mask` correctly. Test early on TOI-270. |
| **Memory issues in multiprocessing** | LOW | LOW | Process one LC at a time per worker. 200 MB per worker × 4 workers = 800 MB. Well within Colab's 12 GB. |
| **Wrong limb darkening for TESS** | MEDIUM | MEDIUM | Do NOT use TLS `catalog_info` (Kepler bandpass). Use Claret 2017 TESS-specific table from VizieR. Pre-download table. |
| **`transitleastsquares` renamed/broken** | LOW | LOW | Pin version in requirements.txt. If issues, fall back to `foldedleastsquares` fork. |
| **L 98-59 b undetectable (400 ppm)** | LOW | MEDIUM | This is near detection limit. Success criterion says "all 3 planets" — if b barely misses SDE 5, adjust: use GP detrending for this specific target or relax to "c and d detected, b sub-threshold." |
| **Stale data in TICv8** | LOW | LOW | TICv8 is mature and well-maintained. Missing values handled with solar defaults. |

---

## Recommended Approach

### Implementation Order

1. **Config + CLI skeleton** (~1h)
   - `config.yaml` with all parameters (periods, thresholds, paths)
   - `run_pipeline.py` with `--sectors`, `--step`, `--dry-run` flags
   - Directory structure creation

2. **Data ingestion module** (`src/ingest.py`) (~2h code, runs during prep week)
   - Bulk MAST query per sector → TIC ID list
   - Batch download FITS → parse to .npz
   - TICv8 stellar parameters → master Parquet
   - Limb darkening table download + per-star interpolation
   - Retry logic, skip+log failures

3. **Preprocessing module** (`src/preprocess.py`) (~2h)
   - Quality flag masking (custom bitmask)
   - 5σ sigma-clipping
   - Median normalization
   - Biweight detrending (wotan)
   - Gap edge flagging
   - Magnitude + cadence filtering (PREP-06)
   - Save preprocessed .npz

4. **Detection module** (`src/detect.py`) (~3h)
   - TLS search with stellar priors
   - Multi-planet iterative search (3 iterations)
   - SDE/SNR/CDPP computation
   - 3-tier SDE gating
   - BLS validation for SDE ≥ 7
   - Save TLS results .npz + update Parquet

5. **Validation** (~2h)
   - WASP-121b detection test (Sector 1)
   - TOI-270 multi-planet test (Sector 3)
   - L 98-59 shallow transit test (Sector 2)
   - Detrending preservation test

6. **GP detrending for top 100** (`src/gp_detrend.py`) (~1h)
   - celerite2 Matérn-3/2 on SDE ≥ 7 candidates
   - Transit-masked fitting
   - Save GP-detrended .npz alongside biweight version

### Key Patterns

- **Modular step functions**: Each module is independently callable (`python -m src.ingest --sector 1`).
- **Per-star try/except**: Never let one star crash the pipeline. Log and continue (D-14).
- **Checkpoint = file existence**: If `data/tls/sector1/TIC_12345_tls.npz` exists, skip that star on resume.
- **JSON-lines logging**: Machine-parseable, one JSON object per log event. Includes timing metrics (D-15).
- **tqdm + structured logs**: Real-time progress bars in terminal, structured data in log file.

### Critical Path

```
[Prep Week]
Day 1-2: Download Sector 1,2,3 data from MAST (overnight runs)
Day 2-3: Build ingest + preprocess modules, validate on WASP-121b
Day 3-5: Build TLS module, run on Sector 1 (overnight), validate
Day 5-6: Run TLS on Sectors 2,3 (overnight each)
Day 6-7: Validate TOI-270 + L 98-59, GP detrending, finalize Parquet

[Hackathon Hour 0]: All Phase 1 outputs ready. Pipeline reads from local cache.
```

---

## RESEARCH COMPLETE
