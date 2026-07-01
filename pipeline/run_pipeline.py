"""
ISRO BAH 2026 PS-07 — Exoplanet Detection Pipeline
Phase 1: Data Ingestion, Preprocessing & Detection
Entrypoint: python pipeline/run_pipeline.py --sectors 1,2,3
"""
import argparse
import sys
import json
import time
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

import pipeline.config as cfg
from pipeline.ingest.download_tess import download_tess_sector
from pipeline.ingest.store import load_lc_npz, save_lc_npz, npz_path
from pipeline.preprocess import (
    apply_quality_mask, apply_sigma_clip, apply_biweight_detrend,
    apply_gap_mask, should_process, get_exclusion_reason,
    get_ld_coefficients,
)
from pipeline.detect import run_tls_batch, apply_sde_gating, save_tls_results
from pipeline.detect.bls_validate import validate_candidates
from pipeline.validate import run_smoke_test

warnings.filterwarnings("ignore")


def preprocess_star(tic_id, sector):
    """Full preprocessing pipeline for a single star. Returns dict with status.
    
    Bug #9 Fix: Now computes and stores median_flux_err for noise injection
    augmentation during training. Also stores flux_normalized key for consistency.
    """
    try:
        lc = load_lc_npz(tic_id, sector, kind='raw')
        time = lc['time']
        flux = lc['flux']
        flux_err = lc['flux_err']
        quality = lc.get('quality')
        meta = lc['meta']

        time, flux, flux_err, quality = apply_quality_mask(
            time, flux, flux_err, quality
        )

        if len(time) < 500:
            return {"tic_id": tic_id, "status": "TOO_FEW_CADENCES"}

        time, flux, flux_err, _ = apply_sigma_clip(time, flux, flux_err, sigma=5.0)

        gap_mask, gaps = apply_gap_mask(time)

        tmag = meta.get('tmag')
        reason = get_exclusion_reason(tmag, len(time[~gap_mask]))
        if reason != "NONE":
            return {"tic_id": tic_id, "status": reason}

        flux_good = flux[~gap_mask]
        time_good = time[~gap_mask]
        flux_err_good = flux_err[~gap_mask]

        if len(time_good) < 500:
            return {"tic_id": tic_id, "status": "TOO_FEW_CADENCES"}

        flat_flux, trend = apply_biweight_detrend(time_good, flux_good)

        meta['gap_mask_gaps'] = [(float(g[0]), float(g[1])) for g in gaps]
        
        # Bug #9 Fix: Compute median_flux_err for noise injection augmentation
        # This is needed by data_generator.py for realistic noise injection
        median_flux_err = float(np.median(flux_err_good))
        meta['median_flux_err'] = median_flux_err
        
        # Bug #10 Fix: Compute flux_normalized (pre-detrending normalized flux)
        # for GP detrending step which expects this key (Plan 05).
        # Normalize to median=1.0 before detrending for GP input
        flux_median = np.median(flux_good)
        flux_normalized = flux_good / flux_median if flux_median > 0 else flux_good

        save_lc_npz(
            tic_id, sector,
            time=time_good, flux=flat_flux,
            flux_err=flux_err_good, quality=None,
            meta=meta, kind='preprocessed',
            # Bug #10: Add flux_normalized for GP detrending step
            flux_normalized=flux_normalized,
        )

        return {
            "tic_id": tic_id, "status": "PREPROCESSED",
            "n_cadences": len(time_good), "n_gaps": len(gaps),
            "median_flux_err": median_flux_err,  # Bug #9: propagate for catalogue
        }
    except FileNotFoundError:
        return {"tic_id": tic_id, "status": "MISSING_RAW"}
    except Exception as e:
        return {"tic_id": tic_id, "status": f"ERROR: {str(e)}"}


def build_master_catalogue(tls_results_df, preprocess_results):
    """Merge TLS results with star metadata into master Parquet catalogue.
    
    Bug #9 Fix: Now includes median_flux_err column for noise injection augmentation.
    """
    if tls_results_df.empty:
        return pd.DataFrame()

    preproc_map = {}
    for res in preprocess_results:
        tic = res.get('tic_id')
        if tic:
            preproc_map[tic] = res

    extra_cols = {}
    tics = tls_results_df['tic_id'].tolist()
    # Bug #9: Add median_flux_err to columns propagated to catalogue
    for col_name in ['tmag', 'ra', 'dec', 'n_cadences', 'n_gaps', 'median_flux_err']:
        extra_cols[col_name] = []
        for tic in tics:
            info = preproc_map.get(tic, {})
            extra_cols[col_name].append(info.get(col_name))

    df = tls_results_df.copy()
    for k, v in extra_cols.items():
        if any(x is not None for x in v):
            df[k] = v

    out_path = Path(cfg.MASTER_CATALOGUE_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    return df


def get_tic_list(sectors):
    """Load TIC IDs to process. Returns list of (tic_id, sector) tuples."""
    raw_dir = Path(cfg.RAW_DIR)
    tic_sector_pairs = []
    for sector in sectors:
        pattern = f"tic*_s{sector:04d}_raw.npz"
        for p in raw_dir.glob(pattern):
            name = p.stem
            tic_str = name.split('_')[0].replace('tic', '')
            tic_id = int(tic_str)
            tic_sector_pairs.append((tic_id, sector))
    return tic_sector_pairs


def main():
    parser = argparse.ArgumentParser(
        description="ISRO BAH 2026 — Exoplanet Detection Pipeline (Phase 1)"
    )
    parser.add_argument(
        "--sectors", type=str, default="1,2,3",
        help="Comma-separated TESS sectors to process (default: 1,2,3)"
    )
    parser.add_argument(
        "--download", action="store_true",
        help="Download TESS data from MAST before processing"
    )
    parser.add_argument(
        "--workers", type=int, default=4,
        help="Parallel workers for download/TLS (default: 4)"
    )
    parser.add_argument(
        "--skip-preprocess", action="store_true",
        help="Skip preprocessing if already done"
    )
    parser.add_argument(
        "--skip-tls", action="store_true",
        help="Skip TLS search if already done"
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Run smoke test validation on catalogue"
    )
    args = parser.parse_args()

    sectors = [int(s.strip()) for s in args.sectors.split(",")]
    t0 = time.time()

    print("=" * 60)
    print("ISRO BAH 2026 — Exoplanet Detection Pipeline")
    print(f"Sectors: {sectors}")
    print("=" * 60)

    # ── Stage 1: Download ──
    if args.download:
        print("\n[Stage 1/4] Downloading TESS data from MAST...")
        for sector in sectors:
            all_tic_ids = _discover_tic_ids(sector)
            if all_tic_ids:
                download_tess_sector(all_tic_ids, sector, workers=args.workers)
            else:
                print(f"  No TIC IDs to download for Sector {sector}")

    # ── Stage 2: Preprocess ──
    if not args.skip_preprocess:
        print("\n[Stage 2/4] Preprocessing light curves...")
        tic_sector_pairs = get_tic_list(sectors)
        if not tic_sector_pairs:
            print("  No raw .npz files found. Run with --download first.")
            sys.exit(1)

        preprocess_results = []
        n = len(tic_sector_pairs)
        for i, (tic, sec) in enumerate(tic_sector_pairs, 1):
            res = preprocess_star(tic, sec)
            preprocess_results.append(res)
            if i % 100 == 0 or i == n:
                statuses = {}
                for r in preprocess_results[-100:]:
                    s = r['status']
                    statuses[s] = statuses.get(s, 0) + 1
                print(f"  Progress: {i}/{n}. Recent: {statuses}")

        n_ok = sum(1 for r in preprocess_results if r['status'] == 'PREPROCESSED')
        print(f"  Preprocessing complete: {n_ok}/{n} stars passed")

    # ── Stage 3: TLS Period Search ──
    if not args.skip_tls:
        print("\n[Stage 3/4] Running TLS period search...")
        star_list = []
        for (tic, sec) in get_tic_list(sectors):
            try:
                lc = load_lc_npz(tic, sec, kind='preprocessed')
                meta = lc['meta']
                u1, u2 = get_ld_coefficients(tic, meta)
                star_list.append((tic, sec, u1, u2))
            except FileNotFoundError:
                continue

        if not star_list:
            print("  No preprocessed .npz files found.")
            sys.exit(1)

        tls_results = run_tls_batch(star_list, workers=args.workers)
        print(f"  TLS search complete: {len(tls_results)} signals found")

        df = apply_sde_gating(tls_results)
        save_tls_results(df)

        n_full = (df['disposition'] == cfg.DISP_FULL_PIPELINE).sum()
        n_sub = (df['disposition'] == cfg.DISP_SUB_THRESHOLD).sum()
        n_disc = (df['disposition'] == cfg.DISP_DISCARD).sum()
        print(f"  SDE gating: {n_full} full pipeline, {n_sub} sub-threshold, {n_disc} discarded")

        # BLS validation on top candidates
        top_candidates = df[df['disposition'] != cfg.DISP_DISCARD].to_dict('records')
        if top_candidates:
            lc_data = {}
            for cand in top_candidates:
                key = (int(cand['tic_id']), int(cand['sector']))
                if key not in lc_data:
                    try:
                        lc_data[key] = load_lc_npz(
                            cand['tic_id'], cand['sector'], kind='preprocessed'
                        )
                    except FileNotFoundError:
                        pass

            top_candidates = validate_candidates(top_candidates, lc_data)
            df_validated = apply_sde_gating([c for c in top_candidates])
            save_tls_results(df_validated)

            n_consistent = sum(1 for c in top_candidates if c.get('bls_consistent'))
            print(f"  BLS validation: {n_consistent}/{len(top_candidates)} consistent")

        # Build master catalogue
        preproc = [{"tic_id": tic, "status": "PREPROCESSED"}
                   for tic, _ in get_tic_list(sectors)]
        build_master_catalogue(df, preproc)

    # ── Stage 4: Validate ──
    if args.validate:
        print("\n[Stage 4/4] Running smoke test validation...")
        passed = run_smoke_test(str(cfg.TLS_RESULTS_PATH))
        if passed:
            print("  All 7 benchmark planets recovered.")
        else:
            print("  Some benchmark planets not recovered — check catalogue.")

    elapsed = (time.time() - t0) / 60.0
    print(f"\nPipeline complete in {elapsed:.1f} minutes.")


def _discover_tic_ids(sector):
    """Discover TIC IDs for a sector from MAST TIC catalogue."""
    try:
        from astroquery.mast import Catalogs
        cat = Catalogs.query_criteria(
            catalog="Tic", sector=sector, objType="STAR"
        )
        if cat is None or len(cat) == 0:
            return []
        return cat['ID'].tolist()
    except Exception:
        return []


if __name__ == "__main__":
    main()
