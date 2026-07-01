# Plan 02-03 Summary: Centroid Analysis + CROWDSAP Gate

**Status:** Complete  
**Phase:** 02 — Intelligence: Feature Engineering & ML Classification  
**Commit:** feat(02-03): Centroid Analysis + CROWDSAP Gate

## What Was Built

Created the `CentroidAnalyzer` class that performs TPF-based flux-weighted centroid shift analysis for blend detection (FEAT-02). This is the core implementation of the centroid pipeline — downloading Target Pixel Files from MAST for the top 200 SDE≥7 candidates, computing per-frame flux-weighted centroids, and updating `centroid_shift_sigma` in the master Parquet catalogue.

### Files Created

- **`src/phase2/centroid_analyzer.py`** — `CentroidAnalyzer` class

### Algorithm

1. **Select candidates**: Top 200 SDE≥7 candidates from master Parquet (sorted by SDE descending)
2. **Download TPF**: lightkurve `search_targetpixelfile()` with SPOC author, cached to `data/tpf/TIC_{id}_s{sector}_tpf.fits`
3. **Build transit mask**: Phase fold using `period`, `t0`, `duration`; check `>= 3` in-transit frames
4. **Flux-weighted centroid**: Per-frame `(sum(flux * x) / sum(flux), sum(flux * y) / sum(flux))`; take median
5. **Shift significance**: `shift_pixels = sqrt((Δcx)² + (Δcy)²)`, `sigma = std(OOT centroid distances)`; `shift_sigma = shift_pixels / sigma`
6. **Blend flag**: `shift_sigma > 3.0` → blend
7. **Update Parquet**: Write `centroid_shift_sigma` column

### CROWDSAP Constants

| Constant | Value | Meaning |
|----------|-------|---------|
| `CENTROID_SHIFT_THRESHOLD_SIGMA` | 3.0 | Blend detection threshold |
| `CROWDSAP_BLOCK_THRESHOLD` | 0.5 | Block PC classification |
| `CROWDSAP_INVESTIGATE_THRESHOLD` | 0.9 | Flag for investigation |

## Verification Results

```
✓ CENTROID_SHIFT_THRESHOLD_SIGMA = 3.0
✓ _compute_centroid_shift: shift_sigma=1.085 (with random flux)
✓ centroid_analyzer.py: all acceptance criteria met
```

## Self-Check: PASSED

## Key Files Created

```yaml
key-files:
  created:
    - src/phase2/centroid_analyzer.py
```

## Requirements Satisfied

- **FEAT-02**: TPF-based centroid shift analysis with 3σ blend detection
