"""TRICERATOPS+ FPP/NFPP computation via isolated conda subprocess.

Runs TRICERATOPS in pre-built 'triceratops_env' conda environment.
Computes False Positive Probability for top 5 Gold planet candidates.
Graceful fallback on failure (D-06): sets status="FAILED", continues pipeline.
"""

import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from src.characterization.utils import (
    append_to_parquet,
    ensure_directories,
    filter_gate2_candidates,
    log_jsonl,
)

logger = logging.getLogger(__name__)

LOG_PATH = "data/logs/pipeline.log"
TRICERATOPS_TIMEOUT = 300  # 5 minutes per candidate


def _classify_fpp(fpp: float | None, nfpp: float | None) -> str:
    """Classify FPP result into disposition category.

    Thresholds per Giacalone et al. 2021:
    - Validated Planet: FPP < 0.015 AND NFPP < 1e-3
    - Likely Planet: FPP < 0.5 AND NFPP < 1e-3
    - Likely Nearby FP: NFPP > 0.1
    """
    if fpp is None or nfpp is None:
        return "FAILED"
    if fpp < 0.015 and nfpp < 0.001:
        return "VALIDATED"
    if fpp < 0.5 and nfpp < 0.001:
        return "LIKELY_PLANET"
    if nfpp > 0.1:
        return "LIKELY_NEARBY_FP"
    return "INCONCLUSIVE"


def run_triceratops_single(tic_id: int, sector: int) -> dict:
    """Run TRICERATOPS on a single candidate via subprocess.

    Executes in isolated 'triceratops_env' conda environment (D-04).
    """
    script_content = f'''
import json
import sys
try:
    import triceratops.triceratops as tr
    target = tr.target(ID={tic_id}, sectors=[{sector}])
    target.calc_probs(time=None, flux_0=None, flux_err_0=None)
    result = {{"FPP": float(target.FPP), "NFPP": float(target.NFPP)}}
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
    sys.exit(1)
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:
        result = subprocess.run(
            ["conda", "run", "-n", "triceratops_env", "python", script_path],
            capture_output=True, text=True, timeout=TRICERATOPS_TIMEOUT,
        )

        if result.returncode != 0:
            return {"tic_id": tic_id, "FPP": None, "NFPP": None,
                    "error": result.stderr[:500] if result.stderr else "Return code non-zero", "status": "FAILED"}

        parsed = json.loads(result.stdout.strip())
        if "error" in parsed:
            return {"tic_id": tic_id, "FPP": None, "NFPP": None,
                    "error": parsed["error"], "status": "FAILED"}

        fpp = parsed["FPP"]
        nfpp = parsed["NFPP"]
        status = _classify_fpp(fpp, nfpp)

        return {"tic_id": tic_id, "FPP": fpp, "NFPP": nfpp, "status": status}

    except subprocess.TimeoutExpired:
        return {"tic_id": tic_id, "FPP": None, "NFPP": None,
                "error": "Timeout", "status": "FAILED"}
    except Exception as e:
        return {"tic_id": tic_id, "FPP": None, "NFPP": None,
                "error": str(e), "status": "FAILED"}
    finally:
        Path(script_path).unlink(missing_ok=True)


def run_triceratops_verification(
    catalogue_path: str = "data/catalogue/master.parquet",
    output_dir: str = "data/verification/triceratops",
    top_n: int = 5,
) -> list[dict]:
    """Run TRICERATOPS+ FPP on top N Gold planet candidates (VAL-04).

    Selects top N from Gate 2 candidates (pc_confidence > 0.85, ranked by SDE × confidence).
    """
    ensure_directories()
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    catalogue = pd.read_parquet(catalogue_path)
    candidates = filter_gate2_candidates(catalogue, top_n=top_n)
    logger.info("TRICERATOPS: running on top %d candidates", len(candidates))

    results = []
    for _, row in tqdm(candidates.iterrows(), total=len(candidates), desc="TRICERATOPS"):
        tic_id = int(row["tic_id"])
        sector = int(row["sector"])

        # Resume: skip if already computed
        out_path = Path(output_dir) / f"{tic_id}.json"
        if out_path.exists():
            try:
                with open(out_path) as f:
                    results.append(json.load(f))
                continue
            except Exception as e:
                logger.warning("Failed to load existing triceratops result for TIC %d, recomputing: %s", tic_id, e)

        t_start = time.time()
        result = run_triceratops_single(tic_id, sector)
        elapsed = time.time() - t_start

        # Save result
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)

        # Append to Parquet
        append_to_parquet(catalogue_path, tic_id, {
            "triceratops_fpp": result.get("FPP"),
            "triceratops_nfpp": result.get("NFPP"),
            "triceratops_status": result["status"],
        })

        log_jsonl(LOG_PATH, {
            "step": "triceratops", "tic_id": tic_id,
            "status": result["status"],
            "fpp": result.get("FPP"),
            "nfpp": result.get("NFPP"),
            "runtime_s": round(elapsed, 3),
        })
        results.append(result)

    n_validated = sum(1 for r in results if r.get("status") == "VALIDATED")
    logger.info("TRICERATOPS complete: %d/%d validated", n_validated, len(results))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_triceratops_verification()
