# Phase 03: Characterization — Parameter Estimation & Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-28
**Phase:** 03-characterization-parameter-estimation-validation
**Areas discussed:** MCMC Priors & Parameter Setup, TRICERATOPS+ & SHERLOCK Integration, Validation Campaign Structure, Diagnostic Plot Pipeline

---

## MCMC Priors & Parameter Setup

### Prior distributions
| Option | Description | Selected |
|--------|-------------|----------|
| Uniform priors with wide bounds | Uniform within [TLS_value ± 5σ] bounds for all parameters | ✓ |
| Normal priors centered on TLS values | Normal(μ=TLS_bestfit, σ=TLS_uncertainty) | |
| Jeffreys priors for scale params | Log-uniform for period, depth, Rp/Rs | |

**User's choice:** Uniform priors with wide bounds
**Notes:** Simplest to implement, least biased.

### Eccentricity handling
| Option | Description | Selected |
|--------|-------------|----------|
| Fix at e=0, ω=90° | Circular orbits, reduces parameter space by 2 | ✓ |
| Fit e and ω with priors | Beta(0.867, 3.03) prior (Kipping 2013) | |

**User's choice:** Fix at e=0, ω=90°

### Parameter bounds
| Option | Description | Selected |
|--------|-------------|----------|
| Dynamic from TLS + star catalog | Period, depth, Rp/Rs bounds from TLS + TICv8 | ✓ |
| Hard-coded astrophysical ranges | Same bounds for every target | |

**User's choice:** Dynamic from TLS + star catalog

### Limb darkening treatment
| Option | Description | Selected |
|--------|-------------|----------|
| Fixed at TICv8 values | Claret & Bloemen (2011) quadratic coefficients fixed | ✓ |
| Sampled with Gaussian priors | Normal(μ=TICv8, σ=0.1×μ) | |

**User's choice:** Fixed at TICv8 values

---

## TRICERATOPS+ & SHERLOCK Integration

### Execution strategy
| Option | Description | Selected |
|--------|-------------|----------|
| Subprocess with isolated conda env | Each tool in own conda env, subprocess.run() | ✓ |
| Direct Python import | Install as pipeline dependencies | |

**User's choice:** Subprocess with isolated conda env
**Notes:** Avoids dependency conflicts with main pipeline stack.

### Pre-install timing
| Option | Description | Selected |
|--------|-------------|----------|
| Pre-build conda envs in prep week | Create and test before hackathon Hour 0 | ✓ |
| Install during hackathon | Build when needed | |

**User's choice:** Pre-build conda envs in prep week
**Notes:** Saves 1-2 hours during the 30-hour window.

### Failure fallback
| Option | Description | Selected |
|--------|-------------|----------|
| Skip tool, flag in output, continue | Verification-only, not gating | ✓ |
| Retry 3× then skip | Adds robustness | |
| Halt pipeline, manual fix | Ensures completeness | |

**User's choice:** Skip tool, flag in output, continue

### Output integration
| Option | Description | Selected |
|--------|-------------|----------|
| JSON result files + Parquet columns | Detailed files + key values in catalogue | ✓ |
| Parquet-only | Parse stdout, append directly | |

**User's choice:** JSON result files + Parquet columns

---

## Validation Campaign Structure

### Validation planet handling
| Option | Description | Selected |
|--------|-------------|----------|
| Separate validation script | validate.py with known-good targets | ✓ |
| Run as regular targets | Full pipeline for all validation planets | |
| Hybrid approach | WASP-121b validation-only, others full pipeline | |

**User's choice:** Separate validation script with known-good targets

### TOI-700 d (Sector 4)
| Option | Description | Selected |
|--------|-------------|----------|
| Download Sector 4 for TOI-700 d only | Special validation-only target | ✓ |
| Substitute with shallow target in Sectors 1-3 | e.g., LHS 3844 b | |
| Skip, cite published values | Literature validation only | |

**User's choice:** Download Sector 4 data for TOI-700 d only

### Validation success criteria
| Option | Description | Selected |
|--------|-------------|----------|
| Quantitative parameter recovery (PARM-06) | Period within 0.1%, depth within 5%, duration within 10% | ✓ |
| Detection + parameter agreement | Must detect AND recover parameters | |

**User's choice:** Quantitative parameter recovery per PARM-06 tolerances

### Validation results storage
| Option | Description | Selected |
|--------|-------------|----------|
| Structured JSON per target + log summary | data/validation/{planet}.json | ✓ |
| Parquet rows in master catalogue | Single table | |

**User's choice:** Structured JSON per target + log summary

---

## Diagnostic Plot Pipeline

### Plot generation structure
| Option | Description | Selected |
|--------|-------------|----------|
| Separate visualization script | generate_diagnostics.py, decoupled from MCMC | ✓ |
| Inline with MCMC run | Each MCMC run generates its own plots | |

**User's choice:** Separate visualization script

### MCMC failure display
| Option | Description | Selected |
|--------|-------------|----------|
| Fallback to Nelder-Mead fit with annotation | Show NM model, flag as non-convergent | ✓ |
| Drop model panel, show error | Missing panel, error message | |
| Show MCMC best-fit regardless | Ignore convergence diagnostics | |

**User's choice:** Fallback to Nelder-Mead fit with annotation

### Plotly interactivity level
| Option | Description | Selected |
|--------|-------------|----------|
| Standard Plotly interactivity | Zoom, pan, hover tooltips, save-as-PNG, annotated epochs | ✓ |
| Minimal Plotly defaults only | Zoom/pan/hover only | |

**User's choice:** Standard Plotly interactivity

### Completeness map
| Option | Description | Selected |
|--------|-------------|----------|
| Recovery fraction heatmap | 20×20 grid, depth vs. period, log-log axes | ✓ |
| Injection scatter plot | Individual points, color-coded by recovery | |

**User's choice:** Recovery fraction heatmap

---

## Deferred Ideas

None — discussion stayed within phase scope.
