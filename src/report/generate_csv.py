"""Candidate catalogue CSV generator — Phase 4 presentation output.

Reads Phase 3 master catalogue Parquet and writes a judge-ready CSV
with exactly 17 columns per RPRT-02/RPRT-03.
"""

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

COLUMNS = [
    "tic_id", "period", "depth", "duration", "sde", "snr",
    "classification", "disposition", "confidence_score", "confidence_tier",
    "period_err", "depth_err", "duration_err",
    "rp_rs", "rp_rs_err", "inclination", "inclination_err",
]

DISPOSITIONS = [
    "PLANET CANDIDATE", "ECLIPSING BINARY", "BACKGROUND BLEND",
    "STELLAR VARIABILITY", "SUB-THRESHOLD",
]

CLASS_NAMES = {0: "PC", 1: "EB", 2: "Blend", 3: "StellarVar"}

TIER_THRESHOLDS = {"GOLD": 0.90, "SILVER": 0.70, "BRONZE": 0.0}


def assign_disposition(classification_label: str, sde: float) -> str:
    if sde < 5:
        return "SUB-THRESHOLD"
    mapping = {
        "PC": "PLANET CANDIDATE",
        "EB": "ECLIPSING BINARY",
        "Blend": "BACKGROUND BLEND",
        "StellarVar": "STELLAR VARIABILITY",
    }
    return mapping.get(classification_label, "SUB-THRESHOLD")


def assign_tier(confidence: float) -> str:
    for tier, threshold in sorted(TIER_THRESHOLDS.items(), key=lambda x: -x[1]):
        if confidence >= threshold:
            return tier
    return "BRONZE"


def generate_catalogue(results_dir: Path, output_path: Path) -> pd.DataFrame:
    catalogue_path = results_dir / "catalogue" / "master_catalogue.parquet"
    if not catalogue_path.exists():
        raise FileNotFoundError(f"Master catalogue not found: {catalogue_path}")

    df = pd.read_parquet(catalogue_path)
    logger.info("Read %d rows from %s", len(df), catalogue_path)

    out = pd.DataFrame()
    out["tic_id"] = df["tic_id"]

    out["period"] = df.get("tls_period", np.nan)
    out["depth"] = df.get("tls_depth", np.nan)
    out["duration"] = df.get("tls_duration", np.nan)
    out["sde"] = df.get("tls_sde", np.nan)
    out["snr"] = df.get("tls_snr", np.nan)

    predicted_class = df.get("predicted_class", pd.Series([-1] * len(df)))
    classification_labels = predicted_class.map(
        lambda x: CLASS_NAMES.get(int(x), "UNKNOWN") if x >= 0 else "UNKNOWN"
    )
    out["classification"] = classification_labels

    sde_vals = df.get("tls_sde", pd.Series([0.0] * len(df)))
    out["disposition"] = [
        assign_disposition(lbl, s)
        for lbl, s in zip(classification_labels, sde_vals)
    ]

    pc_conf = df.get("pc_confidence", pd.Series([0.0] * len(df))).fillna(0.0)
    out["confidence_score"] = pc_conf
    out["confidence_tier"] = pc_conf.apply(assign_tier)

    for col in ["period_err", "depth_err", "duration_err"]:
        out[col] = df.get(col, np.nan)

    out["rp_rs"] = df.get("rp_rs", np.nan)
    out["rp_rs_err"] = df.get("rp_rs_err", np.nan)
    out["inclination"] = df.get("inclination", np.nan)
    out["inclination_err"] = df.get("inclination_err", np.nan)

    dispositions = out["disposition"].unique()
    invalid = set(dispositions) - set(DISPOSITIONS)
    if invalid:
        raise ValueError(f"Invalid dispositions found: {invalid}")

    out = out.sort_values("sde", ascending=False)

    for col in COLUMNS:
        if col not in out.columns:
            out[col] = np.nan

    ordered = out[COLUMNS]
    ordered.to_csv(output_path, index=False, float_format="%.6f")
    logger.info("Wrote catalogue CSV with %d rows to %s", len(ordered), output_path)

    return ordered


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate candidate catalogue CSV")
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    generate_catalogue(args.results_dir, args.output_path)
