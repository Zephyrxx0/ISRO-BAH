"""SHERLOCK independent transit recovery via isolated conda subprocess.

Runs SHERLOCK in pre-built 'sherlock_env' conda environment.
Compares recovery against pipeline detection for top 5 Gold candidates.
Benchmark: SHERLOCK achieves 98% TOI recovery rate (published).
Graceful fallback on failure (D-06): sets status="FAILED", continues pipeline.
"""

import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path

import pandas as pd
import yaml
from tqdm import tqdm

from src.characterization.utils import (
    append_to_parquet,
    ensure_directories,
    filter_gate2_candidates,
    log_jsonl,
)

logger = logging.getLogger(__name__)

LOG_PATH = "data/logs/pipeline.log"
SHERLOCK_TIMEOUT = 600  # 10 minutes per candidate
PERIOD_AGREEMENT_THRESHOLD = 0.001  # 0.1% relative error


def run_sherlock_single(tic_id: int, sectors: list[int],
                        pipeline_period: float) -> dict:
    """Run SHERLOCK on a single candidate via subprocess.

    Executes in isolated 'sherlock_env' conda environment (D-04).
    """
    config = {
        "OBJECTS": {
            f"TIC {tic_id}": {
                "SECTORS": sectors,
                "DETRENDS": ["biweight"],
                "SNR_MIN": 5,
                "SDE_MIN": 5,
                "PERIOD_MIN": 0.5,
                "PERIOD_MAX": 30,
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name

    try:
        result = subprocess.run(
            ["conda", "run", "-n", "sherlock_env", "python", "-m",
             "sherlockpipe", "--properties", config_path],
            capture_output=True, text=True, timeout=SHERLOCK_TIMEOUT,
        )

        if result.returncode != 0:
            return {
                "tic_id": tic_id,
                "sherlock_recovered": None,
                "error": result.stderr[:500] if result.stderr else "Return code non-zero",
                "status": "FAILED",
            }

        # Parse SHERLOCK output for recovered period
        sherlock_period = _parse_sherlock_output(tic_id, result.stdout)

        if sherlock_period is None:
            return {
                "tic_id": tic_id,
                "sherlock_recovered": False,
                "sherlock_period": None,
                "pipeline_period": pipeline_period,
                "status": "NOT_RECOVERED",
            }

        # Compare periods
        period_err = abs(sherlock_period - pipeline_period) / pipeline_period
        agreement_pct = (1 - period_err) * 100
        recovered = period_err < PERIOD_AGREEMENT_THRESHOLD

        verdict = "CONSISTENT" if recovered else "INCONSISTENT"

        return {
            "tic_id": tic_id,
            "sherlock_recovered": recovered,
            "sherlock_period": sherlock_period,
            "pipeline_period": pipeline_period,
            "period_agreement_pct": round(agreement_pct, 4),
            "status": verdict,
        }

    except subprocess.TimeoutExpired:
        return {"tic_id": tic_id, "sherlock_recovered": None,
                "error": "Timeout", "status": "FAILED"}
    except Exception as e:
        return {"tic_id": tic_id, "sherlock_recovered": None,
                "error": str(e), "status": "FAILED"}
    finally:
        Path(config_path).unlink(missing_ok=True)


def _parse_sherlock_output(tic_id: int, stdout: str) -> float | None:
    """Parse SHERLOCK stdout/output for best recovered period.

    Returns best-fit period or None if not recovered.
    """
    # SHERLOCK outputs period in its result summary
    for line in stdout.split("\n"):
        if "period" in line.lower() and "best" in line.lower():
            try:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p.replace(".", "").replace("-", "").isdigit():
                        val = float(p)
                        if 0.5 <= val <= 30.0:
                            return val
            except (ValueError, IndexError):
                continue
    return None


def run_sherlock_verification(
    catalogue_path: str = "data/catalogue/master.parquet",
    output_dir: str = "data/verification/sherlock",
    top_n: int = 5,
) -> list[dict]:
    """Run SHERLOCK independent verification on top N Gold candidates (VAL-05).

    Compares pipeline detection against SHERLOCK's independent transit search.
    Published benchmark: 98% TOI recovery rate.
    """
    ensure_directories()
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    catalogue = pd.read_parquet(catalogue_path)
    candidates = filter_gate2_candidates(catalogue, top_n=top_n)
    logger.info("SHERLOCK: running on top %d candidates", len(candidates))

    results = []
    for _, row in tqdm(candidates.iterrows(), total=len(candidates), desc="SHERLOCK"):
        tic_id = int(row["tic_id"])
        sector = int(row["sector"])
        pipeline_period = float(row["tls_period"])

        # Resume: skip if already computed
        out_path = Path(output_dir) / f"{tic_id}.json"
        if out_path.exists():
            try:
                with open(out_path) as f:
                    results.append(json.load(f))
                continue
            except Exception as e:
                logger.warning("Failed to load existing sherlock result for TIC %d, recomputing: %s", tic_id, e)

        t_start = time.time()
        result = run_sherlock_single(tic_id, [sector], pipeline_period)
        elapsed = time.time() - t_start

        # Save result
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)

        # Append to Parquet
        append_to_parquet(catalogue_path, tic_id, {
            "sherlock_recovered": result.get("sherlock_recovered"),
            "sherlock_status": result["status"],
        })

        log_jsonl(LOG_PATH, {
            "step": "sherlock", "tic_id": tic_id,
            "status": result["status"],
            "sherlock_recovered": result.get("sherlock_recovered"),
            "period_agreement_pct": result.get("period_agreement_pct"),
            "runtime_s": round(elapsed, 3),
        })
        results.append(result)

    n_consistent = sum(1 for r in results if r.get("status") == "CONSISTENT")
    logger.info("SHERLOCK complete: %d/%d consistent with pipeline", n_consistent, len(results))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_sherlock_verification()
