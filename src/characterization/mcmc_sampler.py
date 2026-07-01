"""Gate 2: emcee MCMC posterior estimation for top 15 Gold-tier candidates.

Runs 32 walkers × 5000 steps with HDF5 checkpointing.
Reports median ± 1σ (16th/84th percentile) for 5 parameters.
Generates corner plots with 1σ/2σ contours.
"""

import json
import logging
import time
from pathlib import Path

import batman
import corner
import emcee
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tqdm import tqdm

from src.characterization.utils import (
    append_to_parquet,
    compute_a_rs,
    ensure_directories,
    filter_gate2_candidates,
    get_limb_darkening,
    load_phase_folded,
    log_jsonl,
)

logger = logging.getLogger(__name__)

LOG_PATH = "data/logs/pipeline.log"
NWALKERS = 32
NSTEPS = 5000
NDIM = 5  # rp, inc, a, t0, per


def _log_prior(theta: np.ndarray, bounds: dict) -> float:
    """Uniform priors with dynamic bounds (D-01)."""
    rp, inc, a, t0, per = theta
    if not (bounds["rp_min"] < rp < bounds["rp_max"]):
        return -np.inf
    if not (bounds["inc_min"] < inc < bounds["inc_max"]):
        return -np.inf
    if not (bounds["a_min"] < a < bounds["a_max"]):
        return -np.inf
    if not (bounds["t0_min"] < t0 < bounds["t0_max"]):
        return -np.inf
    if not (bounds["per_min"] < per < bounds["per_max"]):
        return -np.inf
    return 0.0


def _log_likelihood(theta: np.ndarray, t: np.ndarray, flux: np.ndarray,
                    flux_err: np.ndarray, params_template: batman.TransitParams) -> float:
    """Gaussian log-likelihood for batman transit model."""
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


def _log_probability(theta: np.ndarray, t: np.ndarray, flux: np.ndarray,
                     flux_err: np.ndarray, params_template: batman.TransitParams,
                     bounds: dict) -> float:
    """Log-posterior = log-prior + log-likelihood."""
    lp = _log_prior(theta, bounds)
    if not np.isfinite(lp):
        return -np.inf
    ll = _log_likelihood(theta, t, flux, flux_err, params_template)
    if not np.isfinite(ll):
        return -np.inf
    return lp + ll


def _compute_bounds(nm_result: dict, tls_row: pd.Series) -> dict:
    """Compute dynamic uniform prior bounds from NM best-fit (D-01)."""
    rp = nm_result["nm_rp_rs"]
    inc = nm_result["nm_inclination"]
    a = nm_result["nm_a_rs"]
    t0 = nm_result["nm_t0"]
    per = nm_result["nm_period"]
    return {
        "rp_min": max(0.001, rp * 0.3),
        "rp_max": min(0.5, rp * 3.0),
        "inc_min": max(60.0, inc - 15.0),
        "inc_max": 90.0,
        "a_min": max(1.0, a * 0.3),
        "a_max": a * 3.0,
        "t0_min": t0 - 0.1,
        "t0_max": t0 + 0.1,
        "per_min": per * 0.999,
        "per_max": per * 1.001,
    }


def _extract_posteriors(flat_samples: np.ndarray) -> dict:
    """Extract median ± 1σ (16th/50th/84th percentiles) for all parameters."""
    labels = ["rp_rs", "inclination", "a_rs", "t0", "period"]
    posteriors = {}
    for i, label in enumerate(labels):
        q16, q50, q84 = np.percentile(flat_samples[:, i], [16, 50, 84])
        posteriors[f"mcmc_{label}"] = float(q50)
        posteriors[f"mcmc_{label}_err_low"] = float(q50 - q16)
        posteriors[f"mcmc_{label}_err_high"] = float(q84 - q50)

    # Derived: depth in ppm = (rp/rs)^2 * 1e6
    rp_samples = flat_samples[:, 0]
    depth_samples = rp_samples**2 * 1e6
    q16, q50, q84 = np.percentile(depth_samples, [16, 50, 84])
    posteriors["mcmc_depth_ppm"] = float(q50)
    posteriors["mcmc_depth_err_low"] = float(q50 - q16)
    posteriors["mcmc_depth_err_high"] = float(q84 - q50)

    # Derived: duration from a, inc, per (approximate)
    # T14 ≈ (P/π) * arcsin(1/a * sqrt((1+rp)^2 - (a*cos(i))^2) / sin(i))
    a_samples = flat_samples[:, 2]
    inc_samples = np.radians(flat_samples[:, 1])
    per_samples = flat_samples[:, 4]
    cos_i = np.cos(inc_samples)
    sin_i = np.sin(inc_samples)
    rp_s = flat_samples[:, 0]
    arg = (1.0 / a_samples) * np.sqrt(np.maximum((1 + rp_s)**2 - (a_samples * cos_i)**2, 0.0)) / sin_i
    arg = np.clip(arg, -1.0, 1.0)
    duration_samples = (per_samples / np.pi) * np.arcsin(arg)
    q16, q50, q84 = np.percentile(duration_samples[np.isfinite(duration_samples)], [16, 50, 84])
    posteriors["mcmc_duration"] = float(q50)
    posteriors["mcmc_duration_err_low"] = float(q50 - q16)
    posteriors["mcmc_duration_err_high"] = float(q84 - q50)

    return posteriors


def _generate_corner_plot(flat_samples: np.ndarray, tic_id: int, output_dir: str,
                          truths: list | None = None) -> str:
    """Generate corner plot with 1σ, 2σ contours (PARM-05)."""
    labels = [r"$R_p/R_*$", r"$i$ (deg)", r"$a/R_*$", r"$T_0$", r"$P$ (d)"]
    fig = corner.corner(
        flat_samples,
        labels=labels,
        quantiles=[0.16, 0.5, 0.84],
        show_titles=True,
        title_fmt=".5f",
        truths=truths,
        truth_color="red",
        levels=(0.6827, 0.9545),
        smooth=1.0,
        title_kwargs={"fontsize": 10},
    )
    out_path = Path(output_dir) / str(tic_id) / "corner.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out_path)


def _generate_fallback_table(tic_id: int, nm_result: dict, output_dir: str) -> str:
    """Generate parameter table plot when MCMC non-convergent (D-13)."""
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.axis("off")
    table_data = [
        ["Rp/Rs", f"{nm_result['nm_rp_rs']:.6f}"],
        ["Inclination (deg)", f"{nm_result['nm_inclination']:.2f}"],
        ["a/Rs", f"{nm_result['nm_a_rs']:.4f}"],
        ["T0", f"{nm_result['nm_t0']:.6f}"],
        ["Period (d)", f"{nm_result['nm_period']:.7f}"],
    ]
    ax.table(cellText=table_data, colLabels=["Parameter", "Nelder-Mead Value"], loc="center")
    ax.set_title("MCMC Non-Convergent — Nelder-Mead Parameters", fontsize=12)
    out_path = Path(output_dir) / str(tic_id) / "corner.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out_path)


def run_mcmc_single(tic_id: int, nm_result: dict, tls_row: pd.Series,
                    catalogue: pd.DataFrame, folded_dir: str, output_dir: str) -> dict:
    """Run emcee MCMC on a single candidate with HDF5 backend."""
    folded = load_phase_folded(tic_id, folded_dir)
    if folded is None:
        raise FileNotFoundError(f"No folded data for TIC {tic_id}")

    phase_global = folded["phase_global"]
    flux_global = folded["flux_global"]
    flux_err = np.full_like(flux_global, np.std(flux_global) * 0.5)
    flux_err[flux_err < 1e-6] = 1e-4

    # Setup batman template
    ld_coeffs = get_limb_darkening(tic_id, catalogue)
    params_template = batman.TransitParams()
    params_template.ecc = 0.0
    params_template.w = 90.0
    params_template.u = ld_coeffs
    params_template.limb_dark = "quadratic"

    # Time array centered on transit
    t = phase_global * nm_result["nm_period"]

    # Bounds from NM result
    bounds = _compute_bounds(nm_result, tls_row)

    # Initial walker positions: small ball around NM best-fit
    best_fit = np.array([
        nm_result["nm_rp_rs"],
        nm_result["nm_inclination"],
        nm_result["nm_a_rs"],
        nm_result["nm_t0"],
        nm_result["nm_period"],
    ])
    p0 = best_fit + 1e-4 * np.random.randn(NWALKERS, NDIM)

    # HDF5 backend for checkpointing
    chain_path = Path(output_dir) / str(tic_id) / "chain.h5"
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    backend = emcee.backends.HDFBackend(str(chain_path))

    # Resume or reset
    if backend.iteration > 0 and backend.iteration < NSTEPS:
        p0 = backend.get_last_sample()
        remaining = NSTEPS - backend.iteration
    elif backend.iteration >= NSTEPS:
        # Already complete — extract results
        remaining = 0
    else:
        backend.reset(NWALKERS, NDIM)
        remaining = NSTEPS

    sampler = emcee.EnsembleSampler(
        NWALKERS, NDIM, _log_probability,
        args=(t, flux_global, flux_err, params_template, bounds),
        backend=backend,
    )

    if remaining > 0:
        sampler.run_mcmc(p0, remaining, progress=False)

    # Convergence check (PARM-04)
    af = sampler.acceptance_fraction
    converged = bool(np.all((af > 0.2) & (af < 0.5)))

    if not converged:
        logger.warning("MCMC non-convergent for TIC %d (af range: %.3f–%.3f)",
                       tic_id, af.min(), af.max())
        _generate_fallback_table(tic_id, nm_result, output_dir)
        return {
            "tic_id": int(tic_id),
            "mcmc_converged": False,
            "method": "nelder_mead",
            "flag": "MCMC non-convergent — using Nelder-Mead fit",
            "acceptance_fraction_min": float(af.min()),
            "acceptance_fraction_max": float(af.max()),
        }

    # Autocorrelation time
    try:
        tau = sampler.get_autocorr_time(quiet=True)
        burn_in = int(2 * np.max(tau))
        thin = max(1, int(0.5 * np.min(tau)))
    except emcee.autocorr.AutocorrError:
        burn_in = 1000
        thin = 10

    if burn_in >= NSTEPS:
        burn_in = NSTEPS // 2

    flat_samples = sampler.get_chain(discard=burn_in, thin=thin, flat=True)

    # Check effective sample size
    if len(flat_samples) < 100:
        logger.warning("Too few effective samples for TIC %d (%d)", tic_id, len(flat_samples))
        _generate_fallback_table(tic_id, nm_result, output_dir)
        return {
            "tic_id": int(tic_id),
            "mcmc_converged": False,
            "method": "nelder_mead",
            "flag": "MCMC poorly mixed — using Nelder-Mead fit",
        }

    # Extract posteriors (PARM-03)
    posteriors = _extract_posteriors(flat_samples)
    posteriors["tic_id"] = int(tic_id)
    posteriors["mcmc_converged"] = True
    posteriors["method"] = "mcmc"
    posteriors["acceptance_fraction_mean"] = float(np.mean(af))
    posteriors["n_effective_samples"] = int(len(flat_samples))

    # Save posteriors JSON
    post_path = Path(output_dir) / str(tic_id) / "posteriors.json"
    with open(post_path, "w") as f:
        json.dump(posteriors, f, indent=2)

    # Generate corner plot (PARM-05)
    _generate_corner_plot(flat_samples, tic_id, output_dir)

    return posteriors


def run_gate2(
    catalogue_path: str = "data/catalogue/master.parquet",
    output_dir: str = "data/mcmc",
    folded_dir: str = "data/folded",
    resume: bool = True,
) -> list[dict]:
    """Run Gate 2 emcee MCMC on top 15 Gold-tier candidates.

    Entry: SDE >= 7 AND pc_confidence > 0.85, ranked by SDE × pc_confidence (PARM-02).
    """
    ensure_directories()
    catalogue = pd.read_parquet(catalogue_path)
    candidates = filter_gate2_candidates(catalogue, top_n=15)
    logger.info("Gate 2: %d candidates qualify for MCMC", len(candidates))

    results = []
    for _, row in tqdm(candidates.iterrows(), total=len(candidates), desc="Gate 2 MCMC"):
        tic_id = int(row["tic_id"])

        # Check for existing posteriors (resume)
        post_path = Path(output_dir) / str(tic_id) / "posteriors.json"
        if resume and post_path.exists():
            try:
                with open(post_path) as f:
                    results.append(json.load(f))
                continue
            except Exception as e:
                logger.warning("Failed to load existing MCMC posteriors for TIC %d: %s", tic_id, e)

        # Load NM result
        nm_path = Path(output_dir) / str(tic_id) / "nelder_mead.json"
        if not nm_path.exists():
            logger.error("No NM result for TIC %d, skipping MCMC", tic_id)
            continue
        with open(nm_path) as f:
            nm_result = json.load(f)

        t_start = time.time()
        try:
            result = run_mcmc_single(tic_id, nm_result, row, catalogue, folded_dir, output_dir)
        except Exception as e:
            logger.error("Gate 2 MCMC failed for TIC %d: %s", tic_id, e)
            log_jsonl(LOG_PATH, {"step": "gate2", "tic_id": tic_id, "status": "FAILED", "error": str(e)})
            continue

        # Append MCMC columns to Parquet
        if result.get("mcmc_converged"):
            parquet_cols = {k: v for k, v in result.items()
                           if k.startswith("mcmc_") and k != "mcmc_converged"}
            parquet_cols["mcmc_converged"] = True
            append_to_parquet(catalogue_path, tic_id, parquet_cols)
        else:
            append_to_parquet(catalogue_path, tic_id, {"mcmc_converged": False})

        elapsed = time.time() - t_start
        log_jsonl(LOG_PATH, {
            "step": "gate2", "tic_id": tic_id,
            "status": "OK" if result.get("mcmc_converged") else "FALLBACK",
            "converged": result.get("mcmc_converged", False),
            "runtime_s": round(elapsed, 3),
        })
        results.append(result)

    logger.info("Gate 2 complete: %d/%d candidates processed", len(results), len(candidates))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_gate2()
