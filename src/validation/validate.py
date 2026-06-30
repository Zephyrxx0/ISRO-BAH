"""Standalone validation script for known exoplanet parameter recovery.

Runs batman + Nelder-Mead (+ optional MCMC) on known validation targets,
comparing recovered parameters against published literature values.

Usage:
    python -m src.validation.validate [--targets WASP-121b,TOI-270b]
    python -m src.validation.validate --all

This script is SEPARATE from run_pipeline.py (D-08). It loads preprocessed
light curves directly and does NOT run the full detection pipeline.
"""

import argparse
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
    compute_a_rs,
    ensure_directories,
    log_jsonl,
)
from src.validation.published_params import RECOVERY_TOLERANCES, VALIDATION_TARGETS

logger = logging.getLogger(__name__)

LOG_PATH = "data/logs/pipeline.log"
VALIDATION_DIR = "data/validation"


def _load_preprocessed_lc(tic_id: int, sector: int,
                          preprocessed_dir: str = "data/preprocessed") -> dict | None:
    """Load preprocessed light curve for a validation target."""
    path = Path(preprocessed_dir) / f"sector{sector}" / f"TIC_{tic_id}_preprocessed.npz"
    if not path.exists():
        logger.warning("Preprocessed LC not found: %s", path)
        return None
    data = np.load(path)
    return {k: data[k] for k in data.files}


def _run_nm_fit_validation(time_arr: np.ndarray, flux: np.ndarray, flux_err: np.ndarray,
                           published: dict, ld_coeffs: list[float] = None) -> dict:
    """Run Nelder-Mead batman fit initialized from published params.

    For validation, we initialize close to truth to test recovery, not discovery.
    """
    if ld_coeffs is None:
        ld_coeffs = [0.4, 0.2]

    params = batman.TransitParams()
    params.t0 = 0.0
    params.per = published["period"]
    params.rp = published["rp_rs"]
    params.a = published["a_rs"]
    params.inc = published["inclination"]
    params.ecc = 0.0
    params.w = 90.0
    params.u = ld_coeffs
    params.limb_dark = "quadratic"

    # Phase-fold the light curve at the published period
    phase = ((time_arr - time_arr[0]) % published["period"]) / published["period"]
    phase[phase > 0.5] -= 1.0
    sort_idx = np.argsort(phase)
    phase_sorted = phase[sort_idx]
    flux_sorted = flux[sort_idx]
    err_sorted = flux_err[sort_idx]

    # Convert phase to time for batman
    t_model = phase_sorted * published["period"]

    def neg_ll(theta):
        rp, inc, a, t0 = theta
        if rp <= 0 or rp > 0.5 or inc < 60 or inc > 90 or a < 1 or a > 200:
            return 1e10
        params.rp = rp
        params.inc = inc
        params.a = a
        params.t0 = t0
        m = batman.TransitModel(params, t_model)
        model = m.light_curve(params)
        residuals = (flux_sorted - model) / err_sorted
        return 0.5 * np.sum(residuals**2)

    x0 = [published["rp_rs"], published["inclination"], published["a_rs"], 0.0]
    result = minimize(neg_ll, x0, method="Nelder-Mead",
                      options={"maxiter": 10000, "xatol": 1e-8, "fatol": 1e-8})

    rp_fit, inc_fit, a_fit, t0_fit = result.x
    depth_fit = rp_fit**2 * 1e6  # ppm

    # Approximate duration from fitted params
    cos_i = np.cos(np.radians(inc_fit))
    sin_i = np.sin(np.radians(inc_fit))
    arg = (1.0 / a_fit) * np.sqrt(max((1 + rp_fit)**2 - (a_fit * cos_i)**2, 0.0)) / sin_i
    arg = min(max(arg, -1.0), 1.0)
    duration_fit = (published["period"] / np.pi) * np.arcsin(arg)

    return {
        "period": published["period"],  # period not free in Gate 1
        "rp_rs": float(rp_fit),
        "depth_ppm": float(depth_fit),
        "duration_days": float(duration_fit),
        "inclination": float(inc_fit),
        "a_rs": float(a_fit),
        "converged": bool(result.success),
    }


def validate_parameter_recovery(recovered: dict, published: dict) -> dict:
    """Compare recovered vs published parameters (PARM-06, D-10).

    Tolerances: period 0.1%, depth 5%, duration 10%.
    """
    results = {}

    # Period recovery
    if recovered["period"] > 0 and published["period"] > 0:
        period_err = abs(recovered["period"] - published["period"]) / published["period"]
        results["period"] = {
            "recovered": recovered["period"],
            "published": published["period"],
            "error_pct": round(period_err * 100, 4),
            "tolerance_pct": 0.1,
            "pass": period_err < RECOVERY_TOLERANCES["period"],
        }

    # Depth recovery
    depth_err = abs(recovered["depth_ppm"] - published["depth_ppm"]) / published["depth_ppm"]
    results["depth_ppm"] = {
        "recovered": recovered["depth_ppm"],
        "published": published["depth_ppm"],
        "error_pct": round(depth_err * 100, 4),
        "tolerance_pct": 5.0,
        "pass": depth_err < RECOVERY_TOLERANCES["depth_ppm"],
    }

    # Duration recovery
    if recovered["duration_days"] > 0 and published["duration_days"] > 0:
        dur_err = abs(recovered["duration_days"] - published["duration_days"]) / published["duration_days"]
        results["duration_days"] = {
            "recovered": recovered["duration_days"],
            "published": published["duration_days"],
            "error_pct": round(dur_err * 100, 4),
            "tolerance_pct": 10.0,
            "pass": dur_err < RECOVERY_TOLERANCES["duration_days"],
        }

    results["overall_pass"] = all(r["pass"] for r in results.values() if isinstance(r, dict))
    return results


def run_single_validation(name: str, target: dict,
                          preprocessed_dir: str = "data/preprocessed") -> dict:
    """Run validation on a single known target."""
    tic_id = target["tic_id"]
    sector = target["sector"]
    published = target["published"]

    # Load preprocessed light curve
    lc = _load_preprocessed_lc(tic_id, sector, preprocessed_dir)
    if lc is None:
        return {"name": name, "status": "SKIPPED", "reason": "LC not found"}

    time_arr = lc["time"]
    flux = lc["flux"]
    flux_err = lc.get("flux_err", np.full_like(flux, np.std(flux) * 0.5))

    # Run NM fit
    recovered = _run_nm_fit_validation(time_arr, flux, flux_err, published)

    # Compare to published
    comparison = validate_parameter_recovery(recovered, published)

    return {
        "name": name,
        "tic_id": tic_id,
        "sector": sector,
        "source": target["source"],
        "status": "PASS" if comparison["overall_pass"] else "FAIL",
        "recovered": recovered,
        "published": published,
        "comparison": comparison,
    }


def run_validation(
    targets: list[str] | None = None,
    preprocessed_dir: str = "data/preprocessed",
    output_dir: str = VALIDATION_DIR,
) -> list[dict]:
    """Run validation campaign on known targets.

    Args:
        targets: List of target names to validate, or None for all 8.
        preprocessed_dir: Path to preprocessed light curves.
        output_dir: Where to store validation JSON results.
    """
    ensure_directories()
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if targets is None:
        targets = list(VALIDATION_TARGETS.keys())

    results = []
    for name in tqdm(targets, desc="Validation campaign"):
        if name not in VALIDATION_TARGETS:
            logger.warning("Unknown target: %s", name)
            continue

        target = VALIDATION_TARGETS[name]
        t_start = time.time()

        try:
            result = run_single_validation(name, target, preprocessed_dir)
        except Exception as e:
            logger.error("Validation failed for %s: %s", name, e)
            result = {"name": name, "status": "ERROR", "error": str(e)}

        elapsed = time.time() - t_start

        # Save per-target JSON
        out_path = Path(output_dir) / f"{name}.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)

        log_jsonl(LOG_PATH, {
            "step": "validation", "target": name,
            "status": result.get("status", "UNKNOWN"),
            "runtime_s": round(elapsed, 3),
        })
        results.append(result)

    # Summary
    n_pass = sum(1 for r in results if r.get("status") == "PASS")
    logger.info("Validation complete: %d/%d targets PASS", n_pass, len(results))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Validate parameter recovery on known exoplanets")
    parser.add_argument("--targets", type=str, default=None,
                        help="Comma-separated target names (default: all)")
    parser.add_argument("--all", action="store_true", help="Run all 8 targets")
    args = parser.parse_args()

    target_list = None
    if args.targets:
        target_list = [t.strip() for t in args.targets.split(",")]

    run_validation(targets=target_list)
