# Phase 01: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-28
**Phase:** 01-foundation-data-preprocessing-detection
**Areas discussed:** Pipeline execution model, Download & caching strategy, Disk layout & file naming, Progress visibility & failure handling

---

## Pipeline Execution Model

| Option | Description | Selected |
|--------|-------------|----------|
| Modular step functions | Separate modules for ingest, preprocess, detect — each callable independently for testing/debugging | ✓ |
| Single monolithic script | One script that does everything sequentially | |
| You decide | Let planner determine structure | |

| Option | Description | Selected |
|--------|-------------|----------|
| Per-sector batching | Process sectors sequentially, multiprocessing within each sector | ✓ |
| All-sectors parallel | Process all 3 sectors concurrently with multiprocessing | |
| Sequential, no parallelism | Process one star at a time | |
| You decide | Let planner determine parallelism | |

| Option | Description | Selected |
|--------|-------------|----------|
| CLI + config file | CLI for execution flags, YAML/JSON config for parameters | ✓ |
| CLI-only | All parameters as CLI flags | |
| Config file only | All parameters in config file, no CLI | |
| You decide | Let planner determine config strategy | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, via file-based checkpoints | Each stage writes checkpoint per star/sector, skip completed on restart | ✓ |
| No, always run from scratch | No checkpoint complexity | |
| You decide | Let planner determine | |

**User's choice:** Modular step functions, per-sector batching, CLI + config, file-based checkpoints.
**Notes:** User prioritized recoverability from Colab disconnects and debuggability during the 30-hour hackathon window.

---

## Download & Caching Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-download before hackathon | Download all 3 sectors during 7-day prep window | ✓ |
| Download during hackathon runtime | Pipeline downloads from MAST on first run | |
| Hybrid: Sector 1 pre, 2-3 live | Pre-download Sector 1 only | |
| You decide | Let planner determine timing | |

| Option | Description | Selected |
|--------|-------------|----------|
| Structured cache dir | data/raw/sector{1,2,3}/ with .npz per TIC ID | ✓ |
| MAST default cache | Let lightkurve/astroquery use default cache | |
| Single flat directory | data/raw/ with all 60k .npz files | |
| You decide | Let planner determine layout | |

| Option | Description | Selected |
|--------|-------------|----------|
| Retry + skip on failure | Retry 3× with exponential backoff, log and skip on final failure | ✓ |
| Retry until success | Keep retrying indefinitely | |
| Abort on first failure | Stop immediately on any download failure | |
| You decide | Let planner determine retry strategy | |

| Option | Description | Selected |
|--------|-------------|----------|
| Exponential backoff + jitter | Start 1s delay, increase on 429, add random jitter | ✓ |
| Fixed delay | Constant 5s between every MAST request | |
| No delay | Fire requests as fast as possible | |
| You decide | Let planner determine rate-limiting strategy | |

**User's choice:** Pre-download before hackathon, structured cache dir, retry+skip, exponential backoff+jitter.
**Notes:** MAST rate-limiting flagged in STATE.md as a key risk. Pre-download eliminates the dependency entirely during the hackathon.

---

## Disk Layout & File Naming

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror input structure | data/preprocessed/sector{N}/, data/tls/sector{N}/ | ✓ |
| Single outputs/ with type prefixes | outputs/preprocessed/TIC{id}.npz, outputs/tls/TIC{id}.npz | |
| Per-star subdirectories | outputs/TIC{id}/ with all outputs per star | |
| You decide | Let planner determine output layout | |

| Option | Description | Selected |
|--------|-------------|----------|
| Full TIC ID | TIC_123456789_raw.npz, TIC_123456789_preprocessed.npz | ✓ |
| Zero-padded TIC ID | TIC_0000123456789_raw.npz | |
| Sequential numeric index | 00001.npz to 60000.npz with TIC ID mapping in Parquet | |
| You decide | Let planner determine naming | |

| Option | Description | Selected |
|--------|-------------|----------|
| Single master + per-sector | master.parquet + sector_1.parquet etc. | ✓ |
| Single master only | One master.parquet with sector column | |
| Per-sector only, no master | Separate sector files, no single-file view | |
| You decide | Let planner determine catalogue layout | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep intermediates | Preserve all intermediate files on disk | ✓ |
| Pipeline clears intermediates | Delete after each stage | |
| Ephemeral in-memory | No intermediate files written | |
| You decide | Let planner determine intermediate file policy | |

**User's choice:** Mirror input structure, full TIC ID, master + per-sector Parquet, keep intermediates.
**Notes:** Predictable paths for downstream phases. Keeping intermediates enables debugging and re-running individual stages.

---

## Progress Visibility & Failure Handling

| Option | Description | Selected |
|--------|-------------|----------|
| tqdm + log file | Progress bars in terminal + JSON-lines log file | ✓ |
| Print statements only | Simple printed milestones | |
| Silent, log-only | No terminal output, only structured log | |
| You decide | Let planner determine reporting | |

| Option | Description | Selected |
|--------|-------------|----------|
| Skip + log + summary | Catch exceptions, log TIC ID + error, continue, end-of-run summary | ✓ |
| Abort on any failure | Stop entire pipeline if any star fails | |
| Silent skip | Skip bad stars silently, don't log | |
| You decide | Let planner determine failure handling | |

| Option | Description | Selected |
|--------|-------------|----------|
| Structured JSON-lines | One JSON object per line, machine-parseable | ✓ |
| Plain text log | Human-readable text format | |
| No structured log, just tqdm | Terminal progress only, no file log | |
| You decide | Let planner determine log format | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, in log + Parquet | Per-star timing in log and catalogue columns | ✓ |
| No, just total time | Only per-stage total runtime | |
| You decide | Let planner determine metrics tracking | |

**User's choice:** tqdm + JSON-lines log, skip+log+summary, JSON-lines, per-star metrics.
**Notes:** Machine-parseable audit trail preferred for post-run analysis. One bad star shouldn't block 59,999 good ones.

---

## Agent's Discretion

None — user made explicit choices on all questions.

## Deferred Ideas

None — discussion stayed within phase scope.
