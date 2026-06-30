"""Gate 1: Nelder-Mead batman transit model fitting.

Fits batman Mandel-Agol transit model to all candidates with
SDE >= 7 AND pc_confidence > 0.70 using scipy Nelder-Mead optimizer.
"""

import json
import logging
import time
from pathlib import Path

import batman
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from tqdm import tqdm

from src.characterization.utils import (
    append_to_parquet,
    compute_a_rs,
    ensure_directories,
    filter_gate1_candidates,
    get_limb_darkening,
    load_phase_folded,
    log_jsonl,
)

logger = logging.getLogger(__name__)

LOG_PATH = "data/logs/pipeline.log"


def _init_batman_params(tls_row: pd.Series, ld_coeffs: list[float]) -> batman.TransitParams:
    """Initialize batman TransitParams from TLS detection and TICv8."""
    params = batman.TransitParams()
    params.t0 = float(tls_row["tls_t0"])
    params.per = float(tls_row["tls_period"])
    params.rp = np.sqrt(float(tls_row["tls_depth"]))  # depth = (Rp/Rs)^2
    params.a = compute_a_rs(
        float(tls_row["tls_period"]),
        float(tls_row.get("stellar_mass", 1.0)),
        float(tls_row.get("stellar_radius", 1.0)),
    )
    params.inc = 89.0  # initial guess near edge-on
    params.ecc = 0.0  # fixed circular orbit (D-02)
    params.w = 90.0  # fixed (D-02)
    params.u = ld_coeffs  # from TICv8 (D-03)
    params.limb_dark = "quadratic"
    return params


def _neg_log_likelihood(theta: np.ndarray, t: np.ndarray, flux: np.ndarray,
                        flux_err: np.ndarray, params: batman.TransitParams) -> float:
    """Negative log-likelihood for Nelder-Mead minimization.

    Free params: [rp, inc, a, t0]. Period fixed at TLS value.
    """
    rp, inc, a, t0 = theta

    # Physical bounds check
    if rp <= 0 or rp > 0.5:
        return 1e10
    if inc < 60 or inc > 90:
        return 1e10
    if a < 1.0 or a > 200.0:
        return 1e10

    params.rp = rp
    params.inc = inc
    params.a = a
    params.t0 = t0

    m = batman.TransitModel(params, t)
    model = m.light_curve(params)
    residuals = (flux - model) / flux_err
    return 0.5 * np.sum(residuals**2)


def fit_single_candidate(tic_id: int, tls_row: pd.Series, catalogue: pd.DataFrame,
                         folded_dir: str = "data/folded") -> dict | None:
    """Run Nelder-Mead fit on a single candidate.

    Returns dict with best-fit params and chi2, or None on failure.
    """
    # Load phase-folded data
    folded = load_phase_folded(tic_id, folded_dir)
    if folded is None:
        return None

    phase_global = folded["phase_global"]
    flux_global = folded["flux_global"]
    # Estimate flux error from scatter
    flux_err = np.full_like(flux_global, np.std(flux_global) * 0.5)
    flux_err[flux_err < 1e-6] = 1e-4

    # Initialize batman params
    ld_coeffs = get_limb_darkening(tic_id, catalogue)
    params = _init_batman_params(tls_row, ld_coeffs)

    # Convert phase to time relative to t0 for batman
    t = phase_global * params.per
    params.t0 = 0.0  # center on transit

    # Initial guess
    x0 = np.array([params.rp, params.inc, params.a, params.t0])

    # Run Nelder-Mead
    result = minimize(
        _neg_log_likelihood,
        x0,
        args=(t, flux_global, flux_err, params),
        method="Nelder-Mead",
        options={"maxiter": 10000, "xatol": 1e-8, "fatol": 1e-8},
    )

    if not result.success:
        logger.warning("NM fit did not converge for TIC %d: %s", tic_id, result.message)

    # Compute reduced chi-squared
    n_data = len(flux_global)
    n_params = 4
    chi2_red = 2.0 * result.fun / (n_data - n_params)

    rp_fit, inc_fit, a_fit, t0_fit = result.x
    return {
        "tic_id": int(tic_id),
        "nm_rp_rs": float(rp_fit),
        "nm_inclination": float(inc_fit),
        "nm_a_rs": float(a_fit),
        "nm_t0": float(t0_fit),
        "nm_period": float(tls_row["tls_period"]),  # fixed at TLS value
        "nm_chi2": float(chi2_red),
        "nm_converged": bool(result.success),
    }


def run_gate1(
    catalogue_path: str = "data/catalogue/master.parquet",
    output_dir: str = "data/mcmc",
    folded_dir: str = "data/folded",
    resume: bool = True,
) -> list[dict]:
    """Run Gate 1 Nelder-Mead fits on all qualifying candidates.

    Entry criteria: SDE >= 7 AND pc_confidence > 0.70 (PARM-01).
    """
    ensure_directories()
    catalogue = pd.read_parquet(catalogue_path)
    candidates = filter_gate1_candidates(catalogue)
    logger.info("Gate 1: %d candidates qualify (SDE>=7, pc_confidence>0.70)", len(candidates))

    results = []
    for _, row in tqdm(candidates.iterrows(), total=len(candidates), desc="Gate 1 NM fit"):
        tic_id = int(row["tic_id"])
        out_path = Path(output_dir) / str(tic_id) / "nelder_mead.json"

        # Resume: skip if already computed
        if resume and out_path.exists():
            try:
                with open(out_path) as f:
                    results.append(json.load(f))
                continue
            except Exception as e:
                logger.warning("Failed to load existing NM result for TIC %d, recomputing: %s", tic_id, e)

        t_start = time.time()
        try:
            result = fit_single_candidate(tic_id, row, catalogue, folded_dir)
        except Exception as e:
            logger.error("Gate 1 failed for TIC %d: %s", tic_id, e)
            log_jsonl(LOG_PATH, {"step": "gate1", "tic_id": tic_id, "status": "FAILED", "error": str(e)})
            continue

        if result is None:
            continue

        # Save per-candidate JSON
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)

        # Append to master Parquet
        append_to_parquet(catalogue_path, tic_id, {
            "nm_period": result["nm_period"],
            "nm_rp_rs": result["nm_rp_rs"],
            "nm_inclination": result["nm_inclination"],
            "nm_a_rs": result["nm_a_rs"],
            "nm_t0": result["nm_t0"],
            "nm_chi2": result["nm_chi2"],
        })

        elapsed = time.time() - t_start
        log_jsonl(LOG_PATH, {
            "step": "gate1", "tic_id": tic_id, "status": "OK",
            "nm_chi2": result["nm_chi2"], "runtime_s": round(elapsed, 3),
        })
        results.append(result)

    logger.info("Gate 1 complete: %d/%d candidates fitted", len(results), len(candidates))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_gate1()
