# Phase 3 Research: Characterization — Parameter Estimation & Validation

**Researched:** 2026-06-28
**Purpose:** Technical knowledge needed to plan Phase 3 implementation

---

## 1. batman-package API — Transit Model

### Overview
batman (Bad-Ass Transit Model cAlculatioN) implements the Mandel & Agol (2002) analytic transit model. It calculates ~1 million quadratic limb-darkened light curves in 30 seconds on a single core.

### Key Classes

**TransitParams** — stores physical parameters:
| Parameter | Name | Units | Our Usage |
|-----------|------|-------|-----------|
| `t0` | Time of inferior conjunction | days (BJD) | From TLS best-fit epoch |
| `per` | Orbital period | days | From TLS period |
| `rp` | Planet radius / stellar radius | dimensionless | Free parameter, init from TLS depth^0.5 |
| `a` | Semi-major axis / stellar radius | dimensionless | Derived from Kepler's 3rd law + TICv8 |
| `inc` | Orbital inclination | degrees | Free parameter, init ~89° |
| `ecc` | Eccentricity | dimensionless | **Fixed at 0** (D-02) |
| `w` | Argument of periapse | degrees | **Fixed at 90°** (D-02) |
| `u` | Limb darkening coefficients | list | From TICv8 Claret & Bloemen (D-03) |
| `limb_dark` | LD model | string | `"quadratic"` |

**TransitModel** — generates light curves:
```python
import batman
import numpy as np

params = batman.TransitParams()
params.t0 = 0.0
params.per = 1.2749255       # WASP-121b period
params.rp = 0.1218           # Rp/Rs
params.a = 3.86              # a/Rs
params.inc = 87.6
params.ecc = 0.0
params.w = 90.0
params.u = [0.3, 0.2]       # quadratic LD coeffs
params.limb_dark = "quadratic"

t = np.linspace(-0.06, 0.06, 500)  # phase-folded time
m = batman.TransitModel(params, t)
flux = m.light_curve(params)
```

### Integration with Nelder-Mead (scipy)
```python
from scipy.optimize import minimize

def neg_log_likelihood(theta, t, flux, flux_err, params):
    rp, inc, a, t0 = theta
    params.rp = rp
    params.inc = inc
    params.a = a
    params.t0 = t0
    m = batman.TransitModel(params, t)
    model = m.light_curve(params)
    residuals = (flux - model) / flux_err
    return 0.5 * np.sum(residuals**2)

x0 = [rp_init, inc_init, a_init, t0_init]
result = minimize(neg_log_likelihood, x0, args=(t, flux, flux_err, params),
                  method='Nelder-Mead',
                  options={'maxiter': 10000, 'xatol': 1e-8, 'fatol': 1e-8})
```

### Performance Notes
- Quadratic LD: ~30 μs per model evaluation (100 in-transit points)
- For 5 free params × Nelder-Mead (~2000 evaluations): ~60 ms per candidate
- **50 candidates × 60 ms = ~3 seconds total** for Gate 1 (negligible)

---

## 2. emcee 3.1 MCMC — Ensemble Sampler

### Setup Pattern
```python
import emcee

def log_prior(theta):
    rp, inc, a, t0, per = theta
    if not (0.001 < rp < 0.5): return -np.inf
    if not (70.0 < inc < 90.0): return -np.inf
    if not (1.0 < a < 100.0): return -np.inf
    if not (t0_init - 0.1 < t0 < t0_init + 0.1): return -np.inf
    if not (per_init * 0.999 < per < per_init * 1.001): return -np.inf
    return 0.0  # uniform prior

def log_likelihood(theta, t, flux, flux_err, params_template):
    rp, inc, a, t0, per = theta
    params_template.rp = rp
    params_template.inc = inc
    params_template.a = a
    params_template.t0 = t0
    params_template.per = per
    m = batman.TransitModel(params_template, t)
    model = m.light_curve(params_template)
    residuals = (flux - model) / flux_err
    return -0.5 * np.sum(residuals**2 + np.log(2 * np.pi * flux_err**2))

def log_probability(theta, t, flux, flux_err, params_template):
    lp = log_prior(theta)
    if not np.isfinite(lp):
        return -np.inf
    return lp + log_likelihood(theta, t, flux, flux_err, params_template)

ndim = 5  # rp, inc, a, t0, per
nwalkers = 32
# Initialize walkers as small ball around Nelder-Mead best fit
p0 = best_fit + 1e-4 * np.random.randn(nwalkers, ndim)

sampler = emcee.EnsembleSampler(nwalkers, ndim, log_probability,
                                 args=(t, flux, flux_err, params))
sampler.run_mcmc(p0, 5000, progress=True)
```

### Convergence Diagnostics
```python
# Acceptance fraction: target 0.2–0.5
af = sampler.acceptance_fraction
converged = np.all((af > 0.2) & (af < 0.5))

# Autocorrelation time
tau = sampler.get_autocorr_time(quiet=True)
burn_in = int(2 * np.max(tau))
thin = int(0.5 * np.min(tau))

# Extract flat samples (post burn-in, thinned)
flat_samples = sampler.get_chain(discard=burn_in, thin=thin, flat=True)
```

### HDFBackend for Checkpointing
```python
import emcee

filename = f"data/mcmc/{tic_id}/chain.h5"
backend = emcee.backends.HDFBackend(filename)
backend.reset(nwalkers, ndim)

sampler = emcee.EnsembleSampler(nwalkers, ndim, log_probability,
                                 args=(t, flux, flux_err, params),
                                 backend=backend)

# Can resume from checkpoint
if backend.iteration > 0:
    p0 = backend.get_last_sample()
    sampler.run_mcmc(p0, 5000 - backend.iteration, progress=True)
else:
    sampler.run_mcmc(p0, 5000, progress=True)
```

### Parameter Extraction
```python
# Median ± 1σ (16th/84th percentile)
labels = ["rp", "inc", "a", "t0", "per"]
for i, label in enumerate(labels):
    mcmc = np.percentile(flat_samples[:, i], [16, 50, 84])
    median = mcmc[1]
    err_low = mcmc[1] - mcmc[0]
    err_high = mcmc[2] - mcmc[1]
    print(f"{label} = {median:.6f} +{err_high:.6f} -{err_low:.6f}")
```

### Performance Estimates
- batman model eval: ~30 μs (quadratic LD, 200 points)
- Per MCMC step: 32 walkers × 30 μs = ~1 ms
- 5000 steps: ~5 seconds per candidate (single core)
- **15 candidates × 5 seconds = ~75 seconds** (single core, sequential)
- With `multiprocessing.Pool(4)`: ~20 seconds total
- **Risk:** autocorrelation time may require >5000 steps for some targets
- **Mitigation:** monitor tau every 100 steps; extend to 10000 if tau > 1000


---

## 3. Two-Gate Architecture — Pipeline Design

### Gate Logic
```
Phase 2 output: master.parquet (classification, confidence, SDE per candidate)
        │
        ▼
┌─────────────────────────────────────────┐
│ GATE 1: Nelder-Mead batman fit          │
│ Entry: SDE ≥ 7 AND PC_confidence > 0.70 │
│ ~50 candidates                          │
│ Output: best-fit params per candidate   │
│ Time: ~3 seconds total                  │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ GATE 2: Full emcee MCMC                 │
│ Entry: SDE ≥ 7 AND PC_confidence > 0.85 │
│ Ranked by SDE × PC_confidence           │
│ Top 15 only                             │
│ Output: posteriors, corner plots        │
│ Time: ~75 seconds (sequential)          │
└─────────────────────────────────────────┘
```

### Data Flow
1. **Read** from `data/catalogue/master.parquet`: filter rows where `sde >= 7 AND pc_confidence > 0.70`
2. **Load** phase-folded light curve from `data/folded/TIC_{id}_folded.npz` (2001 global view)
3. **Gate 1** runs on all ~50 qualifying candidates:
   - Initialize batman params from TLS period, depth, epoch
   - Compute a/Rs from Kepler's 3rd law using TICv8 stellar mass/radius
   - Run `scipy.optimize.minimize(method='Nelder-Mead')`
   - Store best-fit in `data/mcmc/{TIC_ID}/nelder_mead.json`
   - Append NM parameters to master Parquet
4. **Rank** by `sde * pc_confidence`, select top 15 with `pc_confidence > 0.85`
5. **Gate 2** runs on top 15:
   - Initialize walkers around NM best-fit
   - Run emcee with HDFBackend checkpoint
   - Validate convergence (acceptance fraction, autocorrelation)
   - Extract posteriors, generate corner plots
   - Store chain in `data/mcmc/{TIC_ID}/chain.h5`
   - Store results in `data/mcmc/{TIC_ID}/posteriors.json`
   - Append MCMC parameters + uncertainties to master Parquet

### Non-Convergence Fallback (D-13)
```python
def run_mcmc_with_fallback(tic_id, t, flux, flux_err, nm_result):
    """Run MCMC; fall back to NM if non-convergent."""
    sampler = run_emcee(tic_id, t, flux, flux_err, nm_result)
    af = sampler.acceptance_fraction
    
    if not np.all((af > 0.2) & (af < 0.5)):
        # Non-convergent: flag and use NM results
        return {
            'converged': False,
            'method': 'nelder_mead',
            'params': nm_result,
            'flag': 'MCMC non-convergent — using Nelder-Mead fit'
        }
    
    tau = sampler.get_autocorr_time(quiet=True)
    if np.any(tau > 2500):  # tau > half the chain length
        return {
            'converged': False,
            'method': 'nelder_mead',
            'params': nm_result,
            'flag': 'MCMC poorly mixed — using Nelder-Mead fit'
        }
    
    # Extract posteriors
    burn_in = int(2 * np.max(tau))
    flat_samples = sampler.get_chain(discard=burn_in, flat=True)
    return {
        'converged': True,
        'method': 'mcmc',
        'flat_samples': flat_samples,
        'params': extract_percentiles(flat_samples)
    }
```

---

## 4. TRICERATOPS+ Integration

### Overview
TRICERATOPS (Tool for Rating Interesting Candidate Exoplanets and Reliability Analysis of Transits Originating from Proximate Stars) computes False Positive Probability (FPP) and Nearby FPP (NFPP) for TESS candidates using Bayesian inference with stellar population models.

**Validation thresholds** (Giacalone et al. 2021):
- **Validated Planet:** FPP < 0.015 AND NFPP < 10⁻³
- **Likely Planet:** FPP < 0.5 AND NFPP < 10⁻³
- **Likely Nearby FP:** NFPP > 10⁻¹

### Installation (Isolated Conda Env)
```bash
# Pre-built during 7-day prep window (D-05)
conda create -n triceratops_env python=3.10 -y
conda activate triceratops_env
pip install triceratops lightkurve astroquery
conda deactivate
```

### API Usage Pattern
```python
import triceratops.triceratops as tr

# Create target object
target = tr.target(ID=tic_id, sectors=sectors)

# Calculate false positive probabilities
# Requires: TIC ID, sector(s), aperture/pixel data
target.calc_probs(time=time, flux_0=flux, flux_err_0=flux_err)

# Access results
fpp = target.FPP       # Total false positive probability
nfpp = target.NFPP     # Nearby false positive probability
probs = target.probs   # DataFrame with scenario probabilities
```

### Subprocess Execution (D-04)
```python
import subprocess
import json

def run_triceratops(tic_id, sector, timeout=300):
    """Run TRICERATOPS in isolated conda env via subprocess."""
    script = f'''
import json
import triceratops.triceratops as tr

target = tr.target(ID={tic_id}, sectors=[{sector}])
target.calc_probs(time=time, flux_0=flux, flux_err_0=flux_err)
result = {{"FPP": float(target.FPP), "NFPP": float(target.NFPP)}}
print(json.dumps(result))
'''
    # Write temp script
    script_path = f"/tmp/tric_{tic_id}.py"
    with open(script_path, 'w') as f:
        f.write(script)
    
    result = subprocess.run(
        ["conda", "run", "-n", "triceratops_env", "python", script_path],
        capture_output=True, text=True, timeout=timeout
    )
    
    if result.returncode != 0:
        return {"FPP": None, "NFPP": None, "error": result.stderr}
    
    return json.loads(result.stdout)
```

### Required Inputs
- TIC ID (integer)
- TESS sector number(s)
- Light curve (time, flux, flux_err) — phase-folded or raw
- TPF data (pixel-level) for aperture analysis
- Stellar parameters from TIC (auto-queried by TRICERATOPS)

### Fallback Strategy (D-06)
If TRICERATOPS fails (dependency issue, timeout, Gaia query failure):
- Set `FPP = None`, `NFPP = None` in results
- Flag in Parquet: `triceratops_status = "FAILED"`
- Continue pipeline — TRICERATOPS is verification-only, not gating
- Log error to `data/logs/pipeline.log`

### Risk: Gaia Dependency
TRICERATOPS queries Gaia DR3 for nearby star contamination. During hackathon:
- **Risk:** Gaia TAP service may be slow or unavailable
- **Mitigation:** Pre-cache Gaia queries for validation targets during prep week
- **Fallback:** Skip TRICERATOPS, note in report as "FPP not computed"


---

## 5. SHERLOCK Integration

### Overview
SHERLOCK (Searching for Hints of Exoplanets fRom Lightcurves Of spaCe-based seeKers) is an end-to-end pipeline for searching Kepler/K2/TESS data for transiting planets. Published benchmark: **98% TOI recovery rate** on known TESS objects of interest.

### Installation (Isolated Conda Env)
```bash
# Pre-built during 7-day prep window (D-05)
conda create -n sherlock_env python=3.10 -y
conda activate sherlock_env
pip install sherlockpipe
conda deactivate
```

### Usage Pattern — YAML Configuration
SHERLOCK uses YAML config files to specify targets:
```yaml
# sherlock_config.yaml
OBJECTS:
  TIC {tic_id}:
    SECTORS: [1, 2, 3]
    DETRENDS: 
      - biweight
    SEARCH_ZONE: all
    SNR_MIN: 5
    SDE_MIN: 5
    PERIOD_MIN: 0.5
    PERIOD_MAX: 30
```

### Subprocess Execution (D-04)
```python
import subprocess
import json
import yaml

def run_sherlock(tic_id, sectors, timeout=600):
    """Run SHERLOCK in isolated conda env via subprocess."""
    config = {
        'OBJECTS': {
            f'TIC {tic_id}': {
                'SECTORS': sectors,
                'DETRENDS': ['biweight'],
                'SNR_MIN': 5,
                'SDE_MIN': 5
            }
        }
    }
    config_path = f"/tmp/sherlock_{tic_id}.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    result = subprocess.run(
        ["conda", "run", "-n", "sherlock_env", "python", "-m",
         "sherlockpipe", "--properties", config_path],
        capture_output=True, text=True, timeout=timeout
    )
    
    if result.returncode != 0:
        return {"recovered": None, "error": result.stderr}
    
    # Parse SHERLOCK output directory for results
    return parse_sherlock_output(tic_id)
```

### Comparison Methodology (VAL-05)
For each of the top 5 Gold candidates:
1. Run SHERLOCK independently on the same TESS data
2. Check if SHERLOCK recovers the same period (within 0.1%)
3. Report: `SHERLOCK_recovered = True/False`
4. Aggregate: "Pipeline achieves X/5 recovery vs. SHERLOCK benchmark"
5. Context: cite SHERLOCK's published 98% TOI recovery rate

### Output Format
```json
{
  "tic_id": 261136679,
  "sherlock_recovered": true,
  "sherlock_period": 1.2749,
  "pipeline_period": 1.27493,
  "period_agreement_pct": 99.998,
  "sherlock_sde": 45.2,
  "verdict": "CONSISTENT"
}
```

### Fallback Strategy (D-06)
Same as TRICERATOPS: skip on failure, flag in catalogue, continue pipeline.

---

## 6. corner Package — Posterior Visualization

### Basic Usage with emcee
```python
import corner

# flat_samples shape: (n_samples, ndim)
labels = [r"$R_p/R_*$", r"$i$ (deg)", r"$a/R_*$", r"$T_0$ (BJD)", r"$P$ (d)"]
truths = [published_rp, published_inc, published_a, published_t0, published_per]

fig = corner.corner(
    flat_samples,
    labels=labels,
    quantiles=[0.16, 0.5, 0.84],   # 1σ credible intervals
    show_titles=True,
    title_fmt=".5f",
    truths=truths,                   # published values for validation
    truth_color="red",
    levels=(0.6827, 0.9545),         # 1σ, 2σ contours
    smooth=1.0,
    title_kwargs={"fontsize": 10}
)
fig.savefig(f"data/mcmc/{tic_id}/corner.png", dpi=150, bbox_inches='tight')
```

### Best Practices
- **Extract flat chain:** `sampler.get_chain(discard=burn_in, thin=thin, flat=True)`
- **Burn-in:** discard first `2 × max(tau)` steps
- **Thinning:** thin by `0.5 × min(tau)` to reduce correlation
- **Effective samples:** target > 1000 effective independent samples per parameter
- **Quantiles:** `[0.16, 0.5, 0.84]` gives median ± 1σ in panel titles
- **Levels:** `(0.6827, 0.9545)` for 1σ and 2σ contour regions in 2D panels

### Non-Convergent Fallback (D-13)
When MCMC doesn't converge, replace corner plot with parameter table:
```python
def generate_fallback_plot(tic_id, nm_params):
    """Generate simple parameter table when MCMC fails."""
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.axis('off')
    table_data = [[k, f"{v:.6f}"] for k, v in nm_params.items()]
    table = ax.table(cellText=table_data,
                     colLabels=["Parameter", "Nelder-Mead Value"],
                     loc='center')
    ax.set_title("MCMC Non-Convergent — Nelder-Mead Parameters", fontsize=12)
    fig.savefig(f"data/mcmc/{tic_id}/corner.png", dpi=150, bbox_inches='tight')
```


---

## 7. Diagnostic Plot Generation (VIS-01, VIS-02)

### 4-Panel Layout — matplotlib
```python
import matplotlib.pyplot as plt

def generate_diagnostic_plot(tic_id, data):
    """Generate 4-panel diagnostic PNG for a single candidate."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"TIC {tic_id} — Diagnostic Summary", fontsize=14)
    
    # Panel 1: Raw + Detrended LC with transit epochs
    ax1 = axes[0, 0]
    ax1.scatter(data['time'], data['flux_raw'], s=0.5, alpha=0.3, label='Raw')
    ax1.scatter(data['time'], data['flux_detrended'], s=0.5, alpha=0.7, label='Detrended')
    for epoch in data['transit_epochs']:
        ax1.axvline(epoch, color='red', alpha=0.3, linewidth=0.5)
    ax1.set_xlabel("Time (BJD)")
    ax1.set_ylabel("Relative Flux")
    ax1.legend(fontsize=8)
    ax1.set_title("Light Curve + Transit Epochs")
    
    # Panel 2: TLS Periodogram with peak annotated
    ax2 = axes[0, 1]
    ax2.plot(data['periods'], data['power'], 'k-', linewidth=0.5)
    ax2.axvline(data['best_period'], color='red', linestyle='--')
    ax2.annotate(f"P = {data['best_period']:.5f} d\nSDE = {data['sde']:.1f}",
                 xy=(data['best_period'], data['peak_power']),
                 fontsize=9, color='red')
    ax2.set_xlabel("Period (days)")
    ax2.set_ylabel("SDE")
    ax2.set_title("TLS Periodogram")
    
    # Panel 3: Phase-folded LC + batman model + residuals
    ax3 = axes[1, 0]
    ax3.scatter(data['phase'], data['flux_folded'], s=1, alpha=0.5, color='gray')
    ax3.plot(data['phase_model'], data['model_flux'], 'r-', linewidth=2, label='batman model')
    ax3.set_xlabel("Phase")
    ax3.set_ylabel("Relative Flux")
    ax3.set_title("Phase-Folded + Model")
    # Residuals inset
    ax3_inset = ax3.inset_axes([0.05, 0.05, 0.9, 0.25])
    ax3_inset.scatter(data['phase'], data['residuals'], s=0.5, alpha=0.5)
    ax3_inset.axhline(0, color='red', linewidth=0.5)
    ax3_inset.set_ylabel("Res", fontsize=7)
    
    # Panel 4: Classifier softmax bar chart
    ax4 = axes[1, 1]
    classes = ['PC', 'EB', 'Blend', 'Stellar Var']
    colors = ['green', 'red', 'orange', 'blue']
    ax4.bar(classes, data['softmax_probs'], color=colors)
    ax4.set_ylim(0, 1)
    ax4.set_ylabel("Probability")
    ax4.set_title(f"Classification: {data['disposition']} ({data['confidence']:.2f})")
    
    plt.tight_layout()
    fig.savefig(f"outputs/plots/TIC_{tic_id}_diagnostic.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
```

### Plotly HTML Equivalent (D-14)
```python
import plotly.subplots as sp
import plotly.graph_objects as go

def generate_diagnostic_html(tic_id, data):
    """Generate interactive Plotly HTML diagnostic plot."""
    fig = sp.make_subplots(rows=2, cols=2,
        subplot_titles=["Light Curve + Epochs", "TLS Periodogram",
                        "Phase-Folded + Model", "Classification"])
    
    # Panel 1: LC with hover showing time, flux
    fig.add_trace(go.Scattergl(x=data['time'], y=data['flux_detrended'],
        mode='markers', marker=dict(size=1),
        hovertemplate='Time: %{x:.4f}<br>Flux: %{y:.6f}'), row=1, col=1)
    
    # Panel 2: Periodogram with clickable peaks
    fig.add_trace(go.Scatter(x=data['periods'], y=data['power'],
        mode='lines', line=dict(width=1),
        hovertemplate='P: %{x:.5f} d<br>SDE: %{y:.1f}'), row=1, col=2)
    
    # Panel 3: Phase-fold + model
    fig.add_trace(go.Scattergl(x=data['phase'], y=data['flux_folded'],
        mode='markers', marker=dict(size=2, opacity=0.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=data['phase_model'], y=data['model_flux'],
        mode='lines', line=dict(color='red', width=2)), row=2, col=1)
    
    # Panel 4: Softmax bar
    fig.add_trace(go.Bar(x=['PC','EB','Blend','SV'],
        y=data['softmax_probs'],
        marker_color=['green','red','orange','blue']), row=2, col=2)
    
    fig.update_layout(height=800, width=1200, showlegend=False,
                      title_text=f"TIC {tic_id} Diagnostics")
    fig.write_html(f"outputs/plots/TIC_{tic_id}_diagnostic.html")
```

### Export Settings
- **PNG:** 150 dpi, `bbox_inches='tight'`, ~14×10 inch figure → ~2100×1500 px
- **HTML:** full interactivity (zoom, pan, hover), Plotly.js bundled inline
- **File sizes:** PNG ~200-400 KB each; HTML ~1-2 MB each (Plotly.js included)
- **50 candidates:** ~20 MB PNG + ~75 MB HTML total

---

## 8. Completeness Map (VIS-03)

### Injection-Recovery Methodology
The completeness map characterizes what the pipeline can detect by injecting synthetic transits at known parameters and measuring recovery rate.

### Grid Design (D-15)
- **Depth axis:** 50–2000 ppm, log scale, 20 bins
- **Period axis:** 0.5–30 days, log scale, 20 bins
- **Total cells:** 20 × 20 = 400
- **Injections per cell:** 25 (minimum for statistical significance)
- **Total injections:** 400 × 25 = 10,000

### Implementation
```python
import numpy as np
from itertools import product

def generate_completeness_map(preprocessed_lcs, tls_runner):
    """
    Inject synthetic transits and measure recovery rate.
    Uses Phase 1's TLS pipeline to detect injected signals.
    """
    # Define grid
    depths_ppm = np.logspace(np.log10(50), np.log10(2000), 20)
    periods = np.logspace(np.log10(0.5), np.log10(30), 20)
    n_per_cell = 25
    
    recovery_map = np.zeros((20, 20))
    
    for i, depth in enumerate(depths_ppm):
        for j, period in enumerate(periods):
            n_recovered = 0
            for k in range(n_per_cell):
                # Select random light curve from preprocessed set
                lc = random.choice(preprocessed_lcs)
                
                # Inject batman transit at this depth/period
                rp_rs = np.sqrt(depth * 1e-6)  # depth = (Rp/Rs)^2
                injected_lc = inject_transit(lc, period=period, rp=rp_rs)
                
                # Run TLS detection
                result = tls_runner(injected_lc, period_min=0.5, period_max=30)
                
                # Recovery criterion: detected period within 1% AND SDE ≥ 7
                if (result.sde >= 7 and
                    abs(result.period - period) / period < 0.01):
                    n_recovered += 1
            
            recovery_map[i, j] = n_recovered / n_per_cell
    
    return recovery_map, depths_ppm, periods

def inject_transit(lc, period, rp, inc=89.5, a_rs=15.0):
    """Inject batman transit into existing light curve."""
    params = batman.TransitParams()
    params.t0 = lc['time'][0] + np.random.uniform(0, period)
    params.per = period
    params.rp = rp
    params.a = a_rs
    params.inc = inc
    params.ecc = 0.0
    params.w = 90.0
    params.u = [0.3, 0.2]
    params.limb_dark = "quadratic"
    
    m = batman.TransitModel(params, lc['time'])
    transit_signal = m.light_curve(params)
    
    injected = lc.copy()
    injected['flux'] = lc['flux'] * transit_signal
    return injected
```

### Visualization
```python
def plot_completeness_map(recovery_map, depths_ppm, periods):
    """Generate 2D heatmap of recovery fraction."""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    im = ax.pcolormesh(periods, depths_ppm, recovery_map,
                       cmap='RdYlGn', vmin=0, vmax=1)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel("Orbital Period (days)")
    ax.set_ylabel("Transit Depth (ppm)")
    ax.set_title("Pipeline Completeness Map")
    
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Recovery Fraction")
    
    # Annotate key thresholds
    ax.axhline(84, color='white', linestyle='--', alpha=0.7, label='Earth-analog (84 ppm)')
    ax.axhline(250, color='cyan', linestyle='--', alpha=0.7, label='Super-Earth (~250 ppm)')
    ax.legend(loc='upper left')
    
    fig.savefig("outputs/completeness/completeness_map.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
```

### Performance Estimate
- 10,000 injections × TLS (~2 seconds each) = ~20,000 seconds = **~5.5 hours**
- **This is too slow for the 30-hour hackathon!**
- **Optimization:** Use pre-computed Phase 1 TLS infrastructure. Reduce to:
  - 10 × 10 grid (100 cells) × 10 injections = 1,000 TLS runs = ~33 minutes
  - Or: reuse Phase 2's synthetic injection results (ADR-0003) — 7× augmentation already injected transits at 50–200 ppm. Just tabulate recovery rates from those.
- **Recommended approach:** Leverage the synthetic injection augmentation from Phase 2. Those 7× augmented samples already have known injection parameters. Recovery rate = fraction detected by TLS with SDE ≥ 7.
- **Fallback:** Pre-compute completeness on subset of 500 LCs (not all 60k) with coarse 10×10 grid


---

## 9. Validation Campaign (VAL-01 through VAL-05)

### Published Parameters for Validation Targets

#### WASP-121b (VAL-01 — Day 1 validation)
| Parameter | Value | Source |
|-----------|-------|--------|
| Period | 1.2749255 ± 0.0000003 d | Delrez et al. 2016 |
| Rp/Rs | 0.1218 ± 0.0004 | Delrez et al. 2016 |
| Transit depth | ~14,840 ppm | (0.1218)² |
| Duration (T₁₄) | 0.1203 ± 0.0003 d (2.887 h) | Delrez et al. 2016 |
| Inclination | 87.6 ± 0.7° | Delrez et al. 2016 |
| a/Rs | 3.86 ± 0.02 | Delrez et al. 2016 |
| TESS Sector | 1 | — |
| TIC ID | 22529346 | — |
| Expected SDE | >50 (very deep transit) | — |

#### TOI-270 (VAL-02 — Multi-planet recovery)
| Parameter | TOI-270 b | TOI-270 c | TOI-270 d |
|-----------|-----------|-----------|-----------|
| Period (d) | 3.36016 ± 0.000004 | 5.66057 ± 0.00001 | 11.38014 |
| Rp/Rs | 0.0307 ± 0.0012 | 0.0578 ± 0.0007 | 0.0535 (est.) |
| Depth (ppm) | ~942 | ~3,341 | ~2,862 |
| Radius (R⊕) | 1.28 | 2.33 | 2.13 |
| TESS Sector | 3 | 3 | 3 |
| TIC ID | 259377017 | — | — |
| Source | Günther et al. 2019, Van Eylen et al. 2021 | | |

#### L 98-59 (VAL-02 — Multi-planet recovery)
| Parameter | L 98-59 b | L 98-59 c | L 98-59 d |
|-----------|-----------|-----------|-----------|
| Period (d) | 2.2531140 ± 0.0000004 | 3.6906764 ± 0.0000004 | 7.450729 ± 0.000002 |
| Rp/Rs | 0.0258 ± 0.0004 | 0.0396 ± 0.0003 | 0.0460 ± 0.0006 |
| Depth (ppm) | ~666 | ~1,568 | ~2,116 |
| Radius (R⊕) | 0.84 | 1.33 | 1.63 |
| Duration (h) | ~1.02 | ~1.22 | ~0.9 (grazing) |
| TESS Sector | 2 | 2 | 2 |
| TIC ID | 307210830 | — | — |
| Source | Kostov et al. 2019, Cadieux et al. 2025 | | |

#### TOI-700 d (VAL-03 — Small planet validation)
| Parameter | Value | Source |
|-----------|-------|--------|
| Period | 37.42396 ± 0.00003 d | Gilbert et al. 2020 |
| Radius | 1.07 R⊕ (1.19 R⊕ revised) | Gilbert et al. 2020/2023 |
| Rp/Rs | ~0.015 (estimated) | — |
| Depth | ~225 ppm (shallow!) | — |
| TESS Sector | 4 (special download, D-09) | — |
| TIC ID | 150428135 | — |
| Note | 37.4 d period means only ~1 transit per sector | — |

**Special handling for TOI-700 d:**
- Period of 37.4 days exceeds the ~27-day sector duration
- Only ~0.7 transits per sector — may need multiple sectors for detection
- This is a validation-only target (D-09): download Sector 4 separately
- Recovery validates pipeline's ability to detect shallow transits (~225 ppm)
- May require relaxed SDE threshold for validation (SDE ~5-6)

### Validation Comparison Logic (D-10)
```python
def validate_parameter_recovery(recovered, published, tolerances):
    """
    Compare recovered parameters against published values.
    PARM-06 tolerances: period 0.1%, depth 5%, duration 10%.
    """
    results = {}
    
    # Period recovery
    period_err = abs(recovered['period'] - published['period']) / published['period']
    results['period'] = {
        'recovered': recovered['period'],
        'published': published['period'],
        'error_pct': period_err * 100,
        'tolerance_pct': 0.1,
        'pass': period_err < 0.001
    }
    
    # Depth recovery
    depth_err = abs(recovered['depth'] - published['depth']) / published['depth']
    results['depth'] = {
        'recovered': recovered['depth'],
        'published': published['depth'],
        'error_pct': depth_err * 100,
        'tolerance_pct': 5.0,
        'pass': depth_err < 0.05
    }
    
    # Duration recovery
    dur_err = abs(recovered['duration'] - published['duration']) / published['duration']
    results['duration'] = {
        'recovered': recovered['duration'],
        'published': published['duration'],
        'error_pct': dur_err * 100,
        'tolerance_pct': 10.0,
        'pass': dur_err < 0.10
    }
    
    results['overall_pass'] = all(r['pass'] for r in results.values())
    return results
```

### Validation Script Structure (D-08)
```python
# validate.py — separate from run_pipeline.py
# Downloads and processes known targets, compares to published values

VALIDATION_TARGETS = {
    'WASP-121b': {'tic_id': 22529346, 'sector': 1, 'published': {...}},
    'TOI-270b':  {'tic_id': 259377017, 'sector': 3, 'published': {...}},
    'TOI-270c':  {'tic_id': 259377017, 'sector': 3, 'published': {...}},
    'TOI-270d':  {'tic_id': 259377017, 'sector': 3, 'published': {...}},
    'L98-59b':   {'tic_id': 307210830, 'sector': 2, 'published': {...}},
    'L98-59c':   {'tic_id': 307210830, 'sector': 2, 'published': {...}},
    'L98-59d':   {'tic_id': 307210830, 'sector': 2, 'published': {...}},
    'TOI-700d':  {'tic_id': 150428135, 'sector': 4, 'published': {...}},
}

def run_validation():
    for name, target in VALIDATION_TARGETS.items():
        # 1. Load preprocessed LC (or download + preprocess for TOI-700d)
        # 2. Run batman + NM fit
        # 3. Run MCMC (if Gold-tier equivalent SNR)
        # 4. Compare to published
        # 5. Store results as data/validation/{name}.json
        pass
```


---

## 10. Performance Considerations

### Time Budget Summary
| Task | Candidates | Time per | Total | Parallelizable |
|------|-----------|----------|-------|----------------|
| Gate 1 (NM fit) | ~50 | ~60 ms | ~3 s | Yes (trivial) |
| Gate 2 (emcee 5000 steps) | 15 | ~5 s | ~75 s | Yes (Pool) |
| Corner plots | 15 | ~2 s | ~30 s | Yes |
| Diagnostic PNGs | ~50 | ~3 s | ~150 s | Yes |
| Diagnostic HTMLs | ~50 | ~2 s | ~100 s | Yes |
| TRICERATOPS (subprocess) | 5 | ~60 s | ~5 min | Sequential |
| SHERLOCK (subprocess) | 5 | ~120 s | ~10 min | Sequential |
| Completeness map (optimized) | 1000 injections | ~2 s | ~33 min | Yes (batch) |
| Validation campaign | 8 targets | ~30 s | ~4 min | Yes |
| **TOTAL (sequential)** | | | **~55 min** | |
| **TOTAL (parallelized)** | | | **~40 min** | |

### Critical Path
- **TRICERATOPS + SHERLOCK** dominate if run sequentially (~15 min combined)
- **Completeness map** is the longest single task (~33 min)
- Both are independent of each other — can run in parallel

### Parallelization Strategy
```python
from multiprocessing import Pool
import concurrent.futures

# Gate 2: Parallelize across candidates
with Pool(processes=4) as pool:
    mcmc_results = pool.starmap(run_mcmc_candidate, 
        [(tic_id, data) for tic_id, data in top_15])

# Diagnostic plots: Parallelize across candidates
with Pool(processes=4) as pool:
    pool.map(generate_diagnostic_plot, candidates)

# TRICERATOPS + SHERLOCK: Run in parallel with each other
with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
    tric_future = executor.submit(run_all_triceratops, top_5)
    sher_future = executor.submit(run_all_sherlock, top_5)
    tric_results = tric_future.result()
    sher_results = sher_future.result()
```

### Colab T4 Constraints
- **CPU:** 2 cores (Colab free tier) — limits multiprocessing benefit
- **RAM:** 12.7 GB — sufficient for all MCMC chains in memory
- **Disk:** ~100 GB — more than sufficient for outputs
- **GPU:** Not used for Phase 3 (MCMC is CPU-bound)
- **Session timeout:** 90 minutes idle, 12 hours max — checkpoint critical

### Checkpointing Strategy
1. **Per-candidate MCMC:** HDF5 backend saves chain incrementally
2. **Per-candidate results:** JSON written after each candidate completes
3. **Master Parquet:** updated in batch after Gate 1 completes, then after Gate 2
4. **Diagnostic plots:** generated last, can be re-run independently
5. **Resume logic:** check for existing `posteriors.json` per TIC ID, skip completed

### Memory Management
- emcee chain (32 walkers × 5000 steps × 5 params × 8 bytes) = ~6.4 MB per candidate
- 15 candidates in parallel: ~96 MB — negligible
- Flat samples after thinning: ~0.5 MB per candidate
- Phase-folded LCs (2001 points × 8 bytes × 50 candidates): ~0.8 MB total

---

## 11. Integration with Existing Pipeline

### Input Data Contract (from Phase 2)
**Master Parquet** (`data/catalogue/master.parquet`) — required columns:
```
tic_id, sector, tls_period, tls_t0, tls_sde, tls_snr, tls_depth, tls_duration,
classification, pc_confidence, confidence_tier, 
features_odd_even_depth, features_centroid_shift, features_v_shape
```

**Preprocessed LCs** (`data/preprocessed/sector{N}/TIC_{id}_preprocessed.npz`):
```
Keys: time, flux, flux_raw, flux_err, quality_mask, sector, tic_id
```

**Phase-folded views** (`data/folded/TIC_{id}_folded.npz`):
```
Keys: phase_global (2001 points), flux_global, phase_local (201 points), flux_local
```

### Output Schema (Phase 3 additions to Parquet)
```python
# New columns appended by Phase 3:
phase3_columns = {
    # Gate 1 results (all SDE≥7 + confidence>0.70)
    'nm_period': float,        # Nelder-Mead best-fit period
    'nm_rp_rs': float,         # Nelder-Mead Rp/Rs
    'nm_inclination': float,   # Nelder-Mead inclination
    'nm_a_rs': float,          # Nelder-Mead a/Rs
    'nm_t0': float,            # Nelder-Mead epoch
    'nm_chi2': float,          # Reduced chi-squared of NM fit
    
    # Gate 2 results (top 15 Gold)
    'mcmc_converged': bool,
    'mcmc_period': float,      # MCMC median period
    'mcmc_period_err_low': float,
    'mcmc_period_err_high': float,
    'mcmc_rp_rs': float,
    'mcmc_rp_rs_err_low': float,
    'mcmc_rp_rs_err_high': float,
    'mcmc_inclination': float,
    'mcmc_inclination_err_low': float,
    'mcmc_inclination_err_high': float,
    'mcmc_duration': float,    # Derived from a, inc, P
    'mcmc_duration_err_low': float,
    'mcmc_duration_err_high': float,
    'mcmc_depth_ppm': float,   # (rp_rs)^2 * 1e6
    'mcmc_depth_err_low': float,
    'mcmc_depth_err_high': float,
    
    # Verification results (top 5)
    'triceratops_fpp': float,
    'triceratops_nfpp': float,
    'triceratops_status': str,   # "VALIDATED" / "LIKELY_PLANET" / "FAILED"
    'sherlock_recovered': bool,
    'sherlock_status': str,       # "CONSISTENT" / "NOT_RECOVERED" / "FAILED"
}
```

### Directory Structure
```
data/
├── mcmc/
│   └── {TIC_ID}/
│       ├── nelder_mead.json     # Gate 1 result
│       ├── chain.h5             # emcee HDF5 backend (Gate 2)
│       ├── posteriors.json      # Extracted percentiles
│       └── corner.png           # Corner plot
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
outputs/
├── plots/
│   ├── TIC_{id}_diagnostic.png
│   └── TIC_{id}_diagnostic.html
└── completeness/
    ├── completeness_map.png
    └── completeness_map.html
```

### Module Organization
```
src/
├── characterization/
│   ├── __init__.py
│   ├── nelder_mead_fit.py      # Gate 1: batman + NM optimization
│   ├── mcmc_sampler.py         # Gate 2: emcee MCMC
│   ├── triceratops_runner.py   # Subprocess TRICERATOPS wrapper
│   ├── sherlock_runner.py      # Subprocess SHERLOCK wrapper
│   ├── completeness.py         # Injection-recovery map
│   └── utils.py                # Shared helpers (LD lookup, a/Rs calc)
├── validation/
│   ├── __init__.py
│   ├── validate.py             # Main validation script (D-08)
│   └── published_params.py     # Hardcoded published values
└── visualization/
    ├── __init__.py
    ├── generate_diagnostics.py # 4-panel plots (D-12)
    └── generate_completeness.py
```

### Phase 1/2 Pattern Compliance
- ✅ Modular step functions (separate NM, MCMC, verification, plotting)
- ✅ File-based checkpoints (JSON per TIC ID, HDF5 backend)
- ✅ tqdm progress bars for batch operations
- ✅ JSON-lines logging to `data/logs/pipeline.log`
- ✅ Master Parquet as single source of truth (append columns)
- ✅ .npz per TIC ID for intermediate data
- ✅ Skip + log + continue on per-candidate failures
- ✅ Structured directory layout mirroring Phase 1/2


---

## 12. Risk Areas and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| TRICERATOPS Gaia query fails | Cannot compute FPP | Medium | Pre-cache during prep week; fallback: skip and flag |
| SHERLOCK conda env conflicts | Cannot run SHERLOCK | Low | Pre-build env during prep week; test with known target |
| emcee non-convergence on some candidates | Missing posteriors | Medium | Fallback to NM results; flag in output |
| Completeness map takes too long | Exceeds time budget | High | Use coarse 10×10 grid + fewer injections; leverage Phase 2 synthetics |
| TOI-700 d has P > sector length | Cannot detect in single sector | High | Download multiple sectors; validate as special case with relaxed criteria |
| Colab session timeout during MCMC | Lost progress | Medium | HDF5 backend checkpointing; resume from last state |
| batman TransitModel initialization overhead | Slow if recreated per evaluation | Low | Create model once, reuse with updated params via `m.light_curve(params)` |
| L 98-59 d is grazing (high impact parameter) | Poor parameter recovery | Medium | Wide prior on inclination; report constraint rather than measurement |
| Phase 2 output schema mismatch | Cannot read inputs | Low | Input validation step (`validate_phase2_outputs()`) before processing |
| Validation targets not in Sectors 1-3 | Cannot validate | Low | TOI-700 d is Sector 4 (handled by D-09); all others confirmed in scope |

---

## 13. Dependencies

### Python Packages (Main Environment)
```
batman-package>=2.4.6     # Transit model (Mandel-Agol)
emcee>=3.1.0              # Affine-invariant MCMC
corner>=2.2.0             # Posterior visualization
matplotlib>=3.8           # Static plots
plotly>=5.18              # Interactive HTML plots
scipy>=1.11               # Nelder-Mead optimizer
numpy>=1.26               # Array operations
pandas>=2.1               # Parquet I/O
h5py>=3.9                 # HDF5 backend for emcee chains
tqdm>=4.66                # Progress bars
astropy>=6.0              # Coordinate/time utilities
pyyaml>=6.0               # SHERLOCK config files
```

### Isolated Conda Environments (Pre-built)
```
# triceratops_env:
triceratops>=1.0.19
lightkurve>=2.4
astroquery>=0.4

# sherlock_env:
sherlockpipe>=0.37
```

### Data Dependencies (from Phase 1/2)
- `data/catalogue/master.parquet` with classification + confidence columns
- `data/preprocessed/sector{N}/TIC_*_preprocessed.npz` (detrended LCs)
- `data/folded/TIC_*_folded.npz` (2001 + 201 phase-folded views)
- `data/tpf/` (TPF files for TRICERATOPS aperture analysis)
- TICv8 limb darkening coefficients (pre-extracted in Phase 1, PREP-07)

### External Service Dependencies
- **None at runtime** (all data pre-downloaded)
- TRICERATOPS may query Gaia DR3 — pre-cache during prep week
- SHERLOCK may query MAST — configure to use local data only

---

## 14. Requirement-to-Implementation Mapping

| Req ID | Requirement | Implementation |
|--------|-------------|----------------|
| PARM-01 | batman NM fit on SDE≥7 + confidence>0.70 | `nelder_mead_fit.py` — Gate 1 on ~50 candidates |
| PARM-02 | emcee MCMC (32 walkers, 5000 steps) on top 15 Gold | `mcmc_sampler.py` — Gate 2 with HDFBackend |
| PARM-03 | Report median ± 1σ for P, T₁₄, δ, Rp/Rs, inc | `mcmc_sampler.py` → `posteriors.json` with percentiles |
| PARM-04 | Acceptance fraction 0.2–0.5; fallback to NM | `mcmc_sampler.py` — convergence check + fallback logic |
| PARM-05 | Corner plot with 1σ, 2σ contours | `mcmc_sampler.py` → `corner.png` per MCMC candidate |
| PARM-06 | Period within 0.1%, depth 5%, duration 10% | `validate.py` — compare against published params |
| VAL-01 | Day 1 WASP-121b recovery | `validate.py` — first target, confirms pipeline works |
| VAL-02 | Multi-planet recovery (TOI-270, L 98-59) | `validate.py` — tests iterative detection + fitting |
| VAL-03 | Small-planet TOI-700 d | `validate.py` — Sector 4 special download, shallow transit |
| VAL-04 | TRICERATOPS FPP<1.5%, NFPP<0.1% on top 5 | `triceratops_runner.py` — subprocess in isolated env |
| VAL-05 | SHERLOCK benchmark on top 5 | `sherlock_runner.py` — subprocess in isolated env |
| VIS-01 | 4-panel diagnostic per SDE≥7 candidate | `generate_diagnostics.py` — matplotlib 4-panel |
| VIS-02 | PNG (150 dpi) + Plotly HTML export | `generate_diagnostics.py` — dual export |
| VIS-03 | Completeness map (depth × period heatmap) | `completeness.py` — injection-recovery with batman |

---

## 15. Key Implementation Decisions Summary

1. **batman is fast enough** — 30 μs/model means Gate 1 (50 candidates) takes ~3 seconds
2. **emcee 5000 steps is feasible** — ~75 seconds total for 15 candidates on CPU
3. **HDF5 backend is essential** — Colab sessions can disconnect; checkpoint every step
4. **Completeness map needs optimization** — Full 20×20×25 grid is too slow; use 10×10×10 or leverage Phase 2 synthetics
5. **TRICERATOPS/SHERLOCK are best-effort** — isolated envs pre-built; failures don't block pipeline
6. **Validation script is separate** — `validate.py` runs independently; does not require full 60k pipeline
7. **Diagnostic plots are decoupled** — `generate_diagnostics.py` reads from Parquet + .npz; re-runnable
8. **TOI-700 d is the hardest validation target** — 37.4 d period, ~225 ppm depth, may only get 1 transit per sector

---

## RESEARCH COMPLETE
