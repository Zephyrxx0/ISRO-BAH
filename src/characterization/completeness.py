"""Injection-recovery completeness map computation.

Injects synthetic batman transits at known depth/period combinations
into real preprocessed light curves and measures TLS recovery rate.

Optimized grid: 10×10 × 10 injections = 1000 TLS runs (~33 min on CPU).
"""

import logging
import random
import time
from pathlib import Path

import batman
import numpy as np
from tqdm import tqdm

from src.characterization.utils import ensure_directories, log_jsonl

logger = logging.getLogger(__name__)

LOG_PATH = "data/logs/pipeline.log"

# Grid parameters (D-15 — optimized for hackathon time budget)
N_DEPTH_BINS = 10
N_PERIOD_BINS = 10
N_INJECTIONS_PER_CELL = 10
DEPTH_MIN_PPM = 50
DEPTH_MAX_PPM = 2000
PERIOD_MIN_DAYS = 0.5
PERIOD_MAX_DAYS = 30.0
RECOVERY_SDE_THRESHOLD = 7.0
RECOVERY_PERIOD_TOLERANCE = 0.01  # 1% relative error


def _inject_transit(time_arr: np.ndarray, flux: np.ndarray,
                    period: float, depth_ppm: float) -> tuple[np.ndarray, dict]:
    """Inject synthetic batman transit into light curve.

    Returns (injected_flux, injection_params).
    """
    rp_rs = np.sqrt(depth_ppm * 1e-6)
    t0 = time_arr[0] + random.uniform(0, period)

    params = batman.TransitParams()
    params.t0 = t0
    params.per = period
    params.rp = rp_rs
    params.a = 15.0  # typical a/Rs
    params.inc = 89.5  # near edge-on
    params.ecc = 0.0
    params.w = 90.0
    params.u = [0.4, 0.2]  # typical quadratic LD
    params.limb_dark = "quadratic"

    m = batman.TransitModel(params, time_arr)
    transit_signal = m.light_curve(params)

    injected_flux = flux * transit_signal

    injection_params = {
        "period": period,
        "depth_ppm": depth_ppm,
        "rp_rs": rp_rs,
        "t0": t0,
    }
    return injected_flux, injection_params


def _run_tls_detection(time_arr: np.ndarray, flux: np.ndarray,
                       period_min: float = 0.5, period_max: float = 30.0) -> dict:
    """Run TLS period search on injected light curve.

    Returns dict with best period and SDE.
    """
    try:
        from transitleastsquares import transitleastsquares

        model = transitleastsquares(time_arr, flux)
        results = model.power(
            period_min=period_min,
            period_max=period_max,
            oversampling_factor=3,
            duration_grid_step=1.1,
        )
        return {
            "period": float(results.period),
            "sde": float(results.SDE),
            "snr": float(results.snr) if hasattr(results, "snr") else 0.0,
        }
    except Exception as e:
        logger.debug("TLS failed on injected LC: %s", e)
        return {"period": 0.0, "sde": 0.0, "snr": 0.0}


def _load_random_lcs(preprocessed_dir: str, n_lcs: int = 100) -> list[dict]:
    """Load a random subset of preprocessed light curves for injection."""
    lc_files = list(Path(preprocessed_dir).rglob("TIC_*_preprocessed.npz"))
    if not lc_files:
        raise FileNotFoundError(f"No preprocessed LCs in {preprocessed_dir}")

    selected = random.sample(lc_files, min(n_lcs, len(lc_files)))
    lcs = []
    for path in selected:
        data = np.load(path)
        lcs.append({"time": data["time"], "flux": data["flux"]})
    return lcs


def generate_completeness_map(
    preprocessed_dir: str = "data/preprocessed",
    output_dir: str = "data/completeness",
    n_lcs: int = 100,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run injection-recovery and compute completeness grid.

    Returns (recovery_map, depths_ppm, periods).
    """
    ensure_directories()
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Check for cached result
    grid_path = Path(output_dir) / "recovery_grid.npz"
    if grid_path.exists():
        logger.info("Loading cached completeness grid from %s", grid_path)
        cached = np.load(grid_path)
        return cached["recovery_map"], cached["depths_ppm"], cached["periods"]

    # Define grid
    depths_ppm = np.logspace(np.log10(DEPTH_MIN_PPM), np.log10(DEPTH_MAX_PPM), N_DEPTH_BINS)
    periods = np.logspace(np.log10(PERIOD_MIN_DAYS), np.log10(PERIOD_MAX_DAYS), N_PERIOD_BINS)

    # Load random LCs for injection
    lcs = _load_random_lcs(preprocessed_dir, n_lcs=n_lcs)
    logger.info("Loaded %d light curves for injection-recovery", len(lcs))

    recovery_map = np.zeros((N_DEPTH_BINS, N_PERIOD_BINS))
    total_cells = N_DEPTH_BINS * N_PERIOD_BINS

    t_start = time.time()
    cell_count = 0
    for i, depth in enumerate(tqdm(depths_ppm, desc="Completeness (depth)")):
        for j, period in enumerate(periods):
            n_recovered = 0
            for k in range(N_INJECTIONS_PER_CELL):
                lc = random.choice(lcs)

                # Inject transit
                injected_flux, _ = _inject_transit(lc["time"], lc["flux"], period, depth)

                # Run TLS detection
                det = _run_tls_detection(lc["time"], injected_flux)

                # Recovery criterion: SDE >= 7 AND period within 1%
                if det["sde"] >= RECOVERY_SDE_THRESHOLD:
                    period_err = abs(det["period"] - period) / period
                    if period_err < RECOVERY_PERIOD_TOLERANCE:
                        n_recovered += 1

            recovery_map[i, j] = n_recovered / N_INJECTIONS_PER_CELL
            cell_count += 1

    elapsed = time.time() - t_start

    # Save grid
    np.savez(grid_path, recovery_map=recovery_map, depths_ppm=depths_ppm, periods=periods)

    log_jsonl(LOG_PATH, {
        "step": "completeness",
        "grid_size": f"{N_DEPTH_BINS}x{N_PERIOD_BINS}",
        "n_injections_per_cell": N_INJECTIONS_PER_CELL,
        "total_tls_runs": total_cells * N_INJECTIONS_PER_CELL,
        "runtime_s": round(elapsed, 1),
    })
    logger.info("Completeness map computed in %.1f min", elapsed / 60)

    return recovery_map, depths_ppm, periods


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_completeness_map()
