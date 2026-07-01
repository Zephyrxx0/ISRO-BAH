# Phase 3 Pattern Mapping: Characterization — Parameter Estimation & Validation

**Generated:** 2026-06-28
**Purpose:** Guide the planner in creating concrete, well-structured implementation plans for Phase 3.

---

## 1. Established Patterns (from Phase 1/2)

These conventions are mandatory for all Phase 3 modules:

| Pattern | Description | Phase 3 Application |
|---------|-------------|---------------------|
| Modular step functions | Each stage is a callable module, orchestrated by `run_pipeline.py` | Separate NM fit, MCMC, verification, diagnostics modules |
| File-based checkpoints | Per-star checkpoint files; skip completed on restart | JSON per TIC ID after NM/MCMC; HDF5 backend for emcee chains |
| tqdm progress bars | Real-time terminal feedback on batch operations | All candidate loops (Gate 1, Gate 2, plot generation) |
| JSON-lines logging | Structured log to `data/logs/pipeline.log` | Log each candidate result, validation outcome, tool failure |
| Master Parquet as SSOT | Single `data/catalogue/master.parquet` extended by each phase | Phase 3 appends ~30 new columns (NM params, MCMC posteriors, verification) |
| .npz per TIC ID | Intermediate data stored per-star in structured directories | `data/mcmc/{TIC_ID}/` stores per-candidate MCMC artifacts |
| Skip + log + continue | Catch per-star exceptions, log, continue batch | MCMC non-convergence, TRICERATOPS/SHERLOCK failures |
| Structured directory layout | Sector subdirectories, predictable paths | `data/mcmc/`, `data/validation/`, `data/verification/`, `outputs/plots/` |
| Standalone training scripts | One-time operations separated from `run_pipeline.py` | `validate.py` is standalone; `generate_diagnostics.py` is re-runnable |
| CuPy preference | GPU-accelerated arrays when available | Not applicable to Phase 3 (MCMC is CPU-bound) |
| CLI + config | `--sectors`, `--step` flags; YAML/JSON for parameters | Phase 3 step integrates into `run_pipeline.py --step characterize` |

---

## 2. Directory Structure (All Output Directories)

```
data/
├── mcmc/
│   └── {TIC_ID}/
│       ├── nelder_mead.json        # Gate 1 best-fit parameters
│       ├── chain.h5                # emcee HDF5 backend (Gate 2)
│       ├── posteriors.json         # Extracted median ± 1σ percentiles
│       └── corner.png             # Corner plot (or fallback table)
├── validation/
│   ├── WASP-121b.json
│   ├── TOI-270b.json
│   ├── TOI-270c.json
│   ├── TOI-270d.json
│   ├── L98-59b.json
│   ├── L98-59c.json
│   ├── L98-59d.json
│   └── TOI-700d.json
├── verification/
│   ├── triceratops/
│   │   └── {TIC_ID}.json
│   └── sherlock/
│       └── {TIC_ID}.json
├── catalogue/
│   └── master.parquet             # Extended with Phase 3 columns
└── logs/
    └── pipeline.log               # JSON-lines (appended)

outputs/
├── plots/
│   ├── TIC_{id}_diagnostic.png    # 4-panel matplotlib (150 dpi)
│   └── TIC_{id}_diagnostic.html   # Interactive Plotly equivalent
└── completeness/
    ├── completeness_map.png       # 2D heatmap (150 dpi)
    └── completeness_map.html      # Interactive Plotly version
```

---

## 3. Data Contracts

### 3.1 Input Contract (from Phase 2)

**Master Parquet** — required columns read by Phase 3:
```
tic_id, sector, tls_period, tls_t0, tls_sde, tls_snr, tls_depth, tls_duration,
classification, pc_confidence, confidence_tier,
features_odd_even_depth, features_centroid_shift, features_v_shape,
ra, dec, tess_mag
```

**Preprocessed LCs** (`data/preprocessed/sector{N}/TIC_{id}_preprocessed.npz`):
```
Keys: time, flux, flux_raw, flux_err, quality_mask, sector, tic_id
```

**Phase-folded views** (`data/folded/TIC_{id}_folded.npz`):
```
Keys: phase_global (2001 points), flux_global, phase_local (201 points), flux_local
```

**TICv8 limb darkening** (pre-extracted in Phase 1, PREP-07):
```
Parquet columns: ld_u1, ld_u2 (quadratic coefficients per star)
```

### 3.2 Output Contract (Phase 3 additions to Parquet)

```python
# Gate 1 columns (all SDE≥7 + confidence>0.70 candidates, ~50)
'nm_period': float          # Nelder-Mead best-fit period
'nm_rp_rs': float           # Nelder-Mead Rp/Rs
'nm_inclination': float     # Nelder-Mead inclination (deg)
'nm_a_rs': float            # Nelder-Mead a/Rs
'nm_t0': float              # Nelder-Mead epoch (BJD)
'nm_chi2': float            # Reduced chi-squared of NM fit

# Gate 2 columns (top 15 Gold-tier)
'mcmc_converged': bool
'mcmc_period': float
'mcmc_period_err_low': float
'mcmc_period_err_high': float
'mcmc_rp_rs': float
'mcmc_rp_rs_err_low': float
'mcmc_rp_rs_err_high': float
'mcmc_inclination': float
'mcmc_inclination_err_low': float
'mcmc_inclination_err_high': float
'mcmc_duration': float       # Derived from a, inc, P
'mcmc_duration_err_low': float
'mcmc_duration_err_high': float
'mcmc_depth_ppm': float      # (rp_rs)^2 × 1e6
'mcmc_depth_err_low': float
'mcmc_depth_err_high': float

# Verification columns (top 5 Gold)
'triceratops_fpp': float
'triceratops_nfpp': float
'triceratops_status': str    # "VALIDATED" / "LIKELY_PLANET" / "FAILED"
'sherlock_recovered': bool
'sherlock_status': str        # "CONSISTENT" / "NOT_RECOVERED" / "FAILED"
```

### 3.3 Output Contract (for Phase 4 consumption)

Phase 4 reads:
- `outputs/plots/TIC_{id}_diagnostic.png` — embedded in dashboard per-star view
- `outputs/plots/TIC_{id}_diagnostic.html` — served as interactive page
- `outputs/completeness/completeness_map.png` + `.html` — PDF report Page 3
- `data/catalogue/master.parquet` — all Phase 3 columns for candidate table, CSV export
- `data/validation/*.json` — validation results for PDF report Page 3
- `data/mcmc/{TIC_ID}/corner.png` — MCMC posteriors for PDF report Page 4

---

## 4. Module File Inventory

### 4.1 `src/characterization/__init__.py`
- **Role:** Package init
- **Classification:** module
- **Exports:** `NelderMeadFitter`, `MCMCSampler`, `TriceratopsRunner`, `SherlockRunner`, `CompletenessMapper`

### 4.2 `src/characterization/nelder_mead_fit.py`
- **Role:** Gate 1 — batman transit model + Nelder-Mead optimization
- **Classification:** module
- **Inputs:**
  - `data/catalogue/master.parquet` (filter: `tls_sde >= 7 AND pc_confidence > 0.70`)
  - `data/folded/TIC_{id}_folded.npz` (2001-point global phase-folded view)
  - TICv8 LD coefficients from Parquet (`ld_u1`, `ld_u2`)
  - TICv8 stellar mass/radius for Kepler's 3rd law a/Rs derivation
- **Outputs:**
  - `data/mcmc/{TIC_ID}/nelder_mead.json` (best-fit params + chi2)
  - Appends `nm_*` columns to `master.parquet`
- **Pattern compliance:**
  - Step function: `run_gate1(catalogue_path, output_dir, resume=True)`
  - Checkpoint: skip TIC IDs where `nelder_mead.json` already exists
  - tqdm over ~50 candidates
  - JSON-lines log per candidate (tic_id, nm_chi2, runtime_s)
  - Skip + log on batman model failures (e.g., unphysical params)
- **Key logic:**
  - Initialize batman `TransitParams` from TLS period, depth, epoch
  - Compute `a/Rs` from Kepler's 3rd law + TICv8 stellar mass/radius
  - Fix `ecc=0, w=90, u=[ld_u1, ld_u2], limb_dark="quadratic"` (D-02, D-03)
  - Free params: `[rp, inc, a, t0]` (4 free params; period fixed at TLS value for Gate 1)
  - `scipy.optimize.minimize(method='Nelder-Mead', maxiter=10000)`
  - Compute reduced chi-squared for fit quality assessment
- **Integration:** Called by `run_pipeline.py --step characterize`; feeds Gate 2

### 4.3 `src/characterization/mcmc_sampler.py`
- **Role:** Gate 2 — emcee MCMC posterior estimation
- **Classification:** module
- **Inputs:**
  - `data/catalogue/master.parquet` (filter: `tls_sde >= 7 AND pc_confidence > 0.85`, rank by `sde × pc_confidence`, top 15)
  - `data/mcmc/{TIC_ID}/nelder_mead.json` (initial walker positions)
  - `data/folded/TIC_{id}_folded.npz` (phase-folded LC)
  - TICv8 LD coefficients
- **Outputs:**
  - `data/mcmc/{TIC_ID}/chain.h5` (emcee HDFBackend — incremental checkpoint)
  - `data/mcmc/{TIC_ID}/posteriors.json` (median ± 1σ for 5 params)
  - `data/mcmc/{TIC_ID}/corner.png` (corner plot or fallback table)
  - Appends `mcmc_*` columns to `master.parquet`
- **Pattern compliance:**
  - Step function: `run_gate2(catalogue_path, output_dir, resume=True)`
  - Checkpoint: HDFBackend auto-resumes from last iteration; skip if `posteriors.json` exists
  - tqdm via emcee's `progress=True`
  - JSON-lines log per candidate (tic_id, converged, acceptance_fraction, tau, runtime_s)
  - Skip + log on non-convergence → fallback to NM results (D-13)
- **Key logic:**
  - 5 free params: `[rp, inc, a, t0, per]` (period now free within ±0.1%)
  - Uniform priors with dynamic bounds from TLS + TICv8 (D-01)
  - 32 walkers, 5000 steps (PARM-02)
  - Convergence check: acceptance fraction 0.2–0.5, tau < 2500
  - Extract flat samples: discard `2×max(tau)`, thin by `0.5×min(tau)`
  - Report `[16, 50, 84]` percentiles (PARM-03)
  - Generate corner plot with 1σ/2σ contours (PARM-05)
  - Non-convergent fallback: NM params + flagged parameter table plot (D-13)
- **Integration:** Called after Gate 1 completes; feeds verification and diagnostics

### 4.4 `src/characterization/triceratops_runner.py`
- **Role:** TRICERATOPS+ FPP computation via subprocess
- **Classification:** module
- **Inputs:**
  - `data/catalogue/master.parquet` (top 5 Gold candidates by `sde × pc_confidence`)
  - `data/preprocessed/sector{N}/TIC_{id}_preprocessed.npz` (time, flux, flux_err)
  - `data/tpf/` (TPF pixel data for aperture analysis)
- **Outputs:**
  - `data/verification/triceratops/{TIC_ID}.json` (FPP, NFPP, scenario probs)
  - Appends `triceratops_*` columns to `master.parquet`
- **Pattern compliance:**
  - Step function: `run_triceratops_verification(catalogue_path, output_dir)`
  - Checkpoint: skip TIC IDs where JSON already exists
  - tqdm over 5 candidates
  - JSON-lines log (tic_id, fpp, nfpp, status, runtime_s)
  - Skip + log + continue on failure (D-06): set `triceratops_status = "FAILED"`
- **Key logic:**
  - Write temp Python script per candidate
  - Execute via `subprocess.run(["conda", "run", "-n", "triceratops_env", "python", script])` (D-04)
  - Parse JSON stdout; timeout=300s
  - Classify: FPP<0.015 AND NFPP<1e-3 → "VALIDATED"; FPP<0.5 AND NFPP<1e-3 → "LIKELY_PLANET"
- **Integration:** Runs after Gate 2; results consumed by Phase 4 report

### 4.5 `src/characterization/sherlock_runner.py`
- **Role:** SHERLOCK independent transit recovery via subprocess
- **Classification:** module
- **Inputs:**
  - `data/catalogue/master.parquet` (same top 5 Gold candidates)
  - TESS sector data (local cache from Phase 1)
- **Outputs:**
  - `data/verification/sherlock/{TIC_ID}.json` (recovered period, SDE, verdict)
  - Appends `sherlock_*` columns to `master.parquet`
- **Pattern compliance:**
  - Step function: `run_sherlock_verification(catalogue_path, output_dir)`
  - Checkpoint: skip TIC IDs where JSON already exists
  - tqdm over 5 candidates
  - JSON-lines log (tic_id, sherlock_recovered, period_agreement_pct, runtime_s)
  - Skip + log + continue on failure (D-06): set `sherlock_status = "FAILED"`
- **Key logic:**
  - Generate YAML config per candidate (D-04)
  - Execute via `subprocess.run(["conda", "run", "-n", "sherlock_env", "python", "-m", "sherlockpipe", ...])` 
  - Parse output directory for recovered period; timeout=600s
  - Compare: period within 0.1% → "CONSISTENT"
- **Integration:** Runs in parallel with TRICERATOPS; results for Phase 4 report

### 4.6 `src/characterization/completeness.py`
- **Role:** Injection-recovery completeness map generation
- **Classification:** module
- **Inputs:**
  - `data/preprocessed/sector{N}/TIC_{id}_preprocessed.npz` (subset of ~500 LCs)
  - TLS detection infrastructure from Phase 1 (`src/detection/` module)
  - batman for synthetic transit injection
- **Outputs:**
  - `outputs/completeness/completeness_map.png` (matplotlib heatmap, 150 dpi)
  - `outputs/completeness/completeness_map.html` (Plotly interactive)
  - `data/completeness/recovery_grid.npz` (raw grid data for reproducibility)
- **Pattern compliance:**
  - Step function: `generate_completeness_map(preprocessed_dir, output_dir)`
  - Checkpoint: check if `recovery_grid.npz` exists → skip injection, just re-plot
  - tqdm over grid cells (10×10 or 20×20)
  - JSON-lines log (grid_size, n_injections, total_runtime_s)
- **Key logic:**
  - Optimized grid: 10×10 cells × 10 injections = 1000 TLS runs (~33 min)
  - OR: leverage Phase 2 synthetic augmentation results (ADR-0003) — tabulate existing recovery
  - Depth: 50–2000 ppm (log), Period: 0.5–30 days (log)
  - Recovery = detected with SDE≥7 AND period within 1%
  - Annotate Earth-analog (84 ppm) and Super-Earth (250 ppm) thresholds
- **Integration:** Independent of MCMC; can run in parallel with Gate 2

### 4.7 `src/characterization/utils.py`
- **Role:** Shared helper functions for characterization modules
- **Classification:** utility
- **Functions:**
  - `compute_a_rs(period_days, stellar_mass_solar, stellar_radius_solar)` — Kepler's 3rd law
  - `get_limb_darkening(tic_id, catalogue)` — extract LD coefficients from Parquet
  - `filter_gate1_candidates(catalogue)` — SDE≥7 AND pc_confidence>0.70
  - `filter_gate2_candidates(catalogue)` — SDE≥7 AND pc_confidence>0.85, top 15
  - `append_to_parquet(catalogue_path, tic_id, new_columns)` — thread-safe Parquet update
  - `ensure_directories(base_path)` — create all Phase 3 output directories
  - `load_phase_folded(tic_id)` — load .npz with error handling
- **Pattern compliance:** Pure functions, no side effects except `append_to_parquet`

### 4.8 `src/validation/__init__.py`
- **Role:** Package init
- **Classification:** module
- **Exports:** `run_validation`, `VALIDATION_TARGETS`

### 4.9 `src/validation/published_params.py`
- **Role:** Hardcoded published parameters for known validation exoplanets
- **Classification:** data schema / config
- **Inputs:** None (static data)
- **Outputs:** Dict of published values per target (period, depth, duration, Rp/Rs, inclination, a/Rs)
- **Targets:**
  - WASP-121b (TIC 22529346, Sector 1) — deep transit, Day 1 validation
  - TOI-270 b/c/d (TIC 259377017, Sector 3) — multi-planet
  - L 98-59 b/c/d (TIC 307210830, Sector 2) — multi-planet
  - TOI-700 d (TIC 150428135, Sector 4) — small planet, special download
- **Pattern compliance:** Static dict, no I/O, imported by `validate.py`

### 4.10 `src/validation/validate.py`
- **Role:** Standalone validation script — runs known targets through batman+MCMC, compares to published
- **Classification:** script (standalone, NOT part of `run_pipeline.py`)
- **Inputs:**
  - `data/preprocessed/sector{N}/TIC_{id}_preprocessed.npz` (for validation targets)
  - Published params from `published_params.py`
  - TICv8 LD coefficients
- **Outputs:**
  - `data/validation/{planet_name}.json` (published vs recovered, pass/fail per param)
  - JSON-lines log entries for validation results
- **Pattern compliance:**
  - Standalone entry point: `python -m src.validation.validate` or `python validate.py`
  - tqdm over 8 validation targets
  - JSON-lines log per target (planet_name, period_err_pct, depth_err_pct, duration_err_pct, pass)
  - Does NOT run full detection pipeline — loads preprocessed LC, runs batman+NM+MCMC directly (D-08)
- **Key logic:**
  - Load preprocessed LC for each known target
  - For TOI-700 d: separate Sector 4 download if not cached (D-09)
  - Run Gate 1 (NM fit) + Gate 2 (MCMC) on each target
  - Compare: period within 0.1%, depth within 5%, duration within 10% (PARM-06, D-10)
  - Store structured JSON with per-parameter pass/fail + summary verdict
- **Integration:** Manual run (Day 1 for WASP-121b; end-to-end after full pipeline)

### 4.11 `src/visualization/__init__.py`
- **Role:** Package init
- **Classification:** module
- **Exports:** `generate_all_diagnostics`, `generate_completeness_visualization`

### 4.12 `src/visualization/generate_diagnostics.py`
- **Role:** 4-panel diagnostic plot generation (PNG + Plotly HTML)
- **Classification:** script (decoupled, re-runnable independently per D-12)
- **Inputs:**
  - `data/catalogue/master.parquet` (NM/MCMC params, classification, SDE)
  - `data/preprocessed/sector{N}/TIC_{id}_preprocessed.npz` (raw + detrended flux)
  - `data/folded/TIC_{id}_folded.npz` (phase-folded views)
  - `data/mcmc/{TIC_ID}/nelder_mead.json` or `posteriors.json` (model params for overlay)
- **Outputs:**
  - `outputs/plots/TIC_{id}_diagnostic.png` (14×10 inch, 150 dpi, ~200-400 KB)
  - `outputs/plots/TIC_{id}_diagnostic.html` (Plotly, ~1-2 MB with bundled JS)
- **Pattern compliance:**
  - Step function: `generate_all_diagnostics(catalogue_path, output_dir, resume=True)`
  - Checkpoint: skip TIC IDs where both PNG and HTML already exist
  - tqdm over ~50 SDE≥7 candidates
  - JSON-lines log per candidate (tic_id, png_path, html_path, runtime_s)
  - Skip + log on matplotlib/Plotly render failures
- **Key logic — 4 panels:**
  1. Raw + detrended LC with transit epoch vertical lines
  2. TLS periodogram with peak annotated (period + SDE)
  3. Phase-folded LC + batman model overlay + residuals inset
  4. Classifier softmax bar chart (PC/EB/Blend/SV)
- **Non-convergent MCMC fallback (D-13):** Show NM fit overlay with annotation "MCMC non-convergent"
- **Plotly features (D-14):** zoom, pan, hover tooltips, save-as-PNG, clickable periodogram peaks
- **Integration:** Called by `run_pipeline.py --step visualize`; outputs consumed by Phase 4 dashboard

### 4.13 `src/visualization/generate_completeness.py`
- **Role:** Completeness map visualization (separate from computation)
- **Classification:** script (re-runnable)
- **Inputs:**
  - `data/completeness/recovery_grid.npz` (pre-computed recovery fractions)
- **Outputs:**
  - `outputs/completeness/completeness_map.png` (10×8 inch, 150 dpi)
  - `outputs/completeness/completeness_map.html` (Plotly interactive heatmap)
- **Pattern compliance:**
  - Pure visualization — reads pre-computed data, generates plots
  - Can be called independently for layout refinements
- **Integration:** Called after `completeness.py` computation; outputs for Phase 4 report Page 3


---

## PATTERN MAPPING COMPLETE