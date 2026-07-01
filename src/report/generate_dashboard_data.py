"""Dashboard JSON data generator — Phase 4 presentation output.

Creates candidates.json (all SDE >= 5) and per-star JSON files
(SDE >= 7 only) for the Next.js static dashboard build.
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CLASS_NAMES = {0: "PC", 1: "EB", 2: "Blend", 3: "StellarVar"}
TIER_THRESHOLDS = {"GOLD": 0.90, "SILVER": 0.70, "BRONZE": 0.0}

CANDIDATE_COLUMNS = [
    "tic_id", "period", "depth", "sde", "snr",
    "classification", "disposition", "confidence_score", "confidence_tier", "duration",
]


def _assign_tier(confidence: float) -> str:
    for tier, threshold in sorted(TIER_THRESHOLDS.items(), key=lambda x: -x[1]):
        if confidence >= threshold:
            return tier
    return "BRONZE"


def _class_label(predicted: int) -> str:
    return CLASS_NAMES.get(int(predicted), "UNKNOWN") if predicted >= 0 else "UNKNOWN"


def _disposition(class_label: str, sde: float) -> str:
    if sde < 5:
        return "SUB-THRESHOLD"
    mapping = {
        "PC": "PLANET CANDIDATE",
        "EB": "ECLIPSING BINARY",
        "Blend": "BACKGROUND BLEND",
        "StellarVar": "STELLAR VARIABILITY",
    }
    return mapping.get(class_label, "SUB-THRESHOLD")


def generate_candidates_json(results_dir: Path, output_path: Path) -> None:
    catalogue_path = results_dir / "catalogue" / "master_catalogue.parquet"
    if not catalogue_path.exists():
        raise FileNotFoundError(f"Master catalogue not found: {catalogue_path}")

    df = pd.read_parquet(catalogue_path)
    logger.info("Read %d rows from %s", len(df), catalogue_path)

    out = []
    for _, row in df.iterrows():
        pc_conf = float(row.get("pc_confidence", 0.0) or 0.0)
        sde_val = float(row.get("tls_sde", 0.0) or 0.0)
        cls_label = _class_label(int(row.get("predicted_class", -1)))

        entry = {
            "tic_id": str(row["tic_id"]),
            "period": float(row.get("tls_period", np.nan) or np.nan),
            "depth": float(row.get("tls_depth", np.nan) or np.nan),
            "sde": sde_val,
            "snr": float(row.get("tls_snr", np.nan) or np.nan),
            "classification": cls_label,
            "disposition": _disposition(cls_label, sde_val),
            "confidence_score": pc_conf,
            "confidence_tier": _assign_tier(pc_conf),
            "duration": float(row.get("tls_duration", np.nan) or np.nan),
        }
        out.append(entry)

    with open(output_path, "w") as f:
        json.dump(out, f, indent=2)
    logger.info("Wrote candidates.json with %d entries to %s", len(out), output_path)


def generate_star_jsons(results_dir: Path, output_dir: Path) -> int:
    catalogue_path = results_dir / "catalogue" / "master_catalogue.parquet"
    if not catalogue_path.exists():
        raise FileNotFoundError(f"Master catalogue not found: {catalogue_path}")

    df = pd.read_parquet(catalogue_path)
    sde_mask = df["tls_sde"] >= 7
    sde_candidates = df[sde_mask]
    logger.info("Found %d SDE >= 7 candidates for per-star JSONs", len(sde_candidates))

    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for _, row in sde_candidates.iterrows():
        tic_id = str(row["tic_id"])
        pc_conf = float(row.get("pc_confidence", 0.0) or 0.0)
        sde_val = float(row.get("tls_sde", 0.0) or 0.0)
        cls_label = _class_label(int(row.get("predicted_class", -1)))

        star_json = {
            "tic_id": tic_id,
            "period": float(row.get("tls_period", np.nan) or np.nan),
            "depth": float(row.get("tls_depth", np.nan) or np.nan),
            "duration": float(row.get("tls_duration", np.nan) or np.nan),
            "sde": sde_val,
            "snr": float(row.get("tls_snr", np.nan) or np.nan),
            "classification": cls_label,
            "disposition": _disposition(cls_label, sde_val),
            "confidence_score": pc_conf,
            "confidence_tier": _assign_tier(pc_conf),
            "ra": float(row.get("ra", np.nan) or np.nan),
            "dec": float(row.get("dec", np.nan) or np.nan),
            "rp_rs": float(row.get("rp_rs", np.nan) or np.nan) if "rp_rs" in row else None,
            "rp_rs_err": float(row.get("rp_rs_err", np.nan) or np.nan) if "rp_rs_err" in row else None,
            "inclination": float(row.get("inclination", np.nan) or np.nan) if "inclination" in row else None,
            "inclination_err": float(row.get("inclination_err", np.nan) or np.nan) if "inclination_err" in row else None,
            "period_err": float(row.get("period_err", np.nan) or np.nan) if "period_err" in row else None,
            "depth_err": float(row.get("depth_err", np.nan) or np.nan) if "depth_err" in row else None,
            "duration_err": float(row.get("duration_err", np.nan) or np.nan) if "duration_err" in row else None,
            "plots": {
                "diagnostic_4panel": f"/plots/{tic_id}/diagnostic_4panel.png",
                "periodogram": f"/plots/{tic_id}/periodogram.html",
                "phase_folded": f"/plots/{tic_id}/phase_folded.html",
                "softmax": f"/plots/{tic_id}/softmax.html",
                "corner": f"/plots/{tic_id}/corner.png",
            },
            "triceratops": None,
            "mcmc_available": False,
        }

        tri_path = results_dir / "verification" / "triceratops" / f"{tic_id}.json"
        if tri_path.exists():
            with open(tri_path) as f:
                tri_data = json.load(f)
            star_json["triceratops"] = {
                "fpp": tri_data.get("fpp"),
                "nfpp": tri_data.get("nfpp"),
            }

        mcmc_path = results_dir / f"{tic_id}" / "posteriors.json"
        if mcmc_path.exists():
            star_json["mcmc_available"] = True

        out_path = output_dir / f"{tic_id}.json"
        with open(out_path, "w") as f:
            json.dump(star_json, f, indent=2)
        count += 1

    logger.info("Wrote %d per-star JSON files to %s", count, output_dir)
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dashboard JSON data")
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--candidates-output", type=Path, required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    generate_candidates_json(args.results_dir, args.candidates_output)
    generate_star_jsons(args.results_dir, args.output_dir)
