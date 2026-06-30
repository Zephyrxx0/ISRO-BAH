"""Shared utilities for Phase 3 characterization modules."""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Constants
G = 6.674e-11  # m^3 kg^-1 s^-2
M_SUN = 1.989e30  # kg
R_SUN = 6.957e8  # m
DAY_S = 86400.0  # seconds per day

# Phase 3 output directories
PHASE3_DIRS = [
    "data/mcmc",
    "data/validation",
    "data/verification/triceratops",
    "data/verification/sherlock",
    "data/completeness",
    "outputs/plots",
    "outputs/completeness",
]


def ensure_directories(base_path: str = ".") -> None:
    """Create all Phase 3 output directories."""
    for d in PHASE3_DIRS:
        Path(base_path, d).mkdir(parents=True, exist_ok=True)


def compute_a_rs(period_days: float, stellar_mass_solar: float, stellar_radius_solar: float) -> float:
    """Compute semi-major axis in stellar radii via Kepler's 3rd law.

    a/Rs = ((G * M_star * P^2) / (4 * pi^2))^(1/3) / R_star
    """
    period_s = period_days * DAY_S
    m_star = stellar_mass_solar * M_SUN
    r_star = stellar_radius_solar * R_SUN
    a_m = ((G * m_star * period_s**2) / (4 * np.pi**2)) ** (1.0 / 3.0)
    return a_m / r_star


def get_limb_darkening(tic_id: int, catalogue: pd.DataFrame) -> list[float]:
    """Extract quadratic limb darkening coefficients from master Parquet.

    Returns [u1, u2] from TICv8 Claret & Bloemen (2011) values.
    Falls back to [0.4, 0.2] if columns missing.
    """
    row = catalogue.loc[catalogue["tic_id"] == tic_id]
    if row.empty:
        logger.warning("TIC %d not in catalogue, using default LD [0.4, 0.2]", tic_id)
        return [0.4, 0.2]
    if "ld_u1" in row.columns and "ld_u2" in row.columns:
        u1 = float(row["ld_u1"].iloc[0])
        u2 = float(row["ld_u2"].iloc[0])
        if np.isnan(u1) or np.isnan(u2):
            return [0.4, 0.2]
        return [u1, u2]
    logger.warning("LD columns missing for TIC %d, using default [0.4, 0.2]", tic_id)
    return [0.4, 0.2]


def filter_gate1_candidates(catalogue: pd.DataFrame) -> pd.DataFrame:
    """Filter candidates for Gate 1: SDE >= 7 AND pc_confidence > 0.70."""
    mask = (catalogue["tls_sde"] >= 7) & (catalogue["pc_confidence"] > 0.70)
    return catalogue[mask].copy()


def filter_gate2_candidates(catalogue: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Filter candidates for Gate 2: SDE >= 7 AND pc_confidence > 0.85, top N by SDE * pc_confidence."""
    mask = (catalogue["tls_sde"] >= 7) & (catalogue["pc_confidence"] > 0.85)
    filtered = catalogue[mask].copy()
    filtered["rank_score"] = filtered["tls_sde"] * filtered["pc_confidence"]
    filtered = filtered.sort_values("rank_score", ascending=False).head(top_n)
    return filtered.drop(columns=["rank_score"])


def append_to_parquet(catalogue_path: str, tic_id: int, new_columns: dict) -> None:
    """Append new column values for a single TIC ID to master Parquet."""
    df = pd.read_parquet(catalogue_path)
    for col, val in new_columns.items():
        if col not in df.columns:
            df[col] = np.nan
        df.loc[df["tic_id"] == tic_id, col] = val
    df.to_parquet(catalogue_path, index=False)


def load_phase_folded(tic_id: int, folded_dir: str = "data/folded") -> dict | None:
    """Load phase-folded .npz for a TIC ID. Returns dict or None on failure."""
    path = Path(folded_dir) / f"TIC_{tic_id}_folded.npz"
    if not path.exists():
        logger.warning("Phase-folded file not found: %s", path)
        return None
    data = np.load(path)
    return {k: data[k] for k in data.files}


def log_jsonl(log_path: str, entry: dict) -> None:
    """Append a JSON-lines log entry."""
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
