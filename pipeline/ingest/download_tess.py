import numpy as np
import lightkurve as lk
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pipeline.config as cfg
from pipeline.ingest.store import save_lc_npz


def _get_tic_crowdsap(tic_id):
    """Query TIC for CROWDSAP (contamination ratio) for a target.
    
    CROWDSAP = 1 - contratio, where contratio is the fraction of flux
    from contaminating sources. CROWDSAP near 1 means clean target.
    
    Bug #3 Fix: TIC stores 'contratio', but we need CROWDSAP = 1 - contratio.
    """
    try:
        from astroquery.mast import Catalogs
        result = Catalogs.query_criteria(catalog="TIC", ID=str(tic_id))
        if result is None or len(result) == 0:
            return 1.0  # Default: assume clean
        
        row = result[0]
        # TIC 'contratio' is contamination ratio (flux from neighbors / total)
        # CROWDSAP = 1 - contratio (fraction of flux from target star)
        contratio = row.get('contratio', 0.0)
        if contratio is None or np.ma.is_masked(contratio) or np.isnan(contratio):
            return 1.0
        
        # Bug #3 Fix: Correct inversion - CROWDSAP = 1 - contratio
        crowdsap = 1.0 - float(contratio)
        return max(0.0, min(1.0, crowdsap))  # Clamp to [0, 1]
    except Exception:
        return 1.0  # Default on error


def _download_single_tic(tic_id, sector, quality_bitmask=175):
    """Download and store a single TESS light curve as .npz."""
    try:
        path = Path(_npz_path(tic_id, sector, kind='raw'))
        if path.exists():
            return {"tic_id": tic_id, "status": "EXISTS"}

        search = lk.search_lightcurve(
            f"TIC {tic_id}", mission="TESS", sector=sector, cadence=120
        )
        if len(search) == 0:
            return {"tic_id": tic_id, "status": "NOT_FOUND"}

        lc_collection = search.download_all(quality_bitmask=quality_bitmask)
        if lc_collection is None or len(lc_collection) == 0:
            return {"tic_id": tic_id, "status": "DOWNLOAD_FAILED"}

        lc = lc_collection.stitch()
        
        # Query CROWDSAP from TIC (Bug #3 fix)
        crowdsap = _get_tic_crowdsap(tic_id)

        meta = {
            "tic_id": tic_id,
            "sector": sector,
            "ra": getattr(lc, "ra", None),
            "dec": getattr(lc, "dec", None),
            "tmag": getattr(lc, "tess_mag", None),
            "teff": getattr(lc, "teff", None),
            "crowdsap": crowdsap,  # Bug #3: Now correctly computed as 1 - contratio
        }

        save_lc_npz(
            tic_id, sector,
            time=lc.time.value,
            flux=lc.flux.value,
            flux_err=lc.flux_err.value,
            quality=lc.quality if hasattr(lc, "quality") else None,
            meta=meta,
            kind="raw",
        )
        return {"tic_id": tic_id, "status": "SUCCESS", "meta": meta}
    except Exception as e:
        return {"tic_id": tic_id, "status": f"ERROR: {str(e)}"}


def _npz_path(tic_id, sector, kind='raw'):
    base = cfg.RAW_DIR if kind == 'raw' else cfg.PREP_DIR
    return base / f"tic{tic_id:016d}_s{sector:04d}_{kind}.npz"


def download_tess_sector(tic_ids, sector, workers=4, limit=None):
    """Download TESS 2-min cadence light curves for a sector."""
    targets = tic_ids[:limit] if limit is not None else tic_ids
    counts = {"SUCCESS": 0, "EXISTS": 0, "NOT_FOUND": 0, "DOWNLOAD_FAILED": 0, "ERROR": 0}
    results = []

    print(f"Downloading {len(targets)} TESS Sector {sector} light curves ({workers} workers)...")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_download_single_tic, tic, sector): tic
            for tic in targets
        }
        for i, future in enumerate(as_completed(futures), 1):
            tic = futures[future]
            try:
                res = future.result()
                status = res["status"]
                if status.startswith("ERROR"):
                    counts["ERROR"] += 1
                else:
                    counts[status] = counts.get(status, 0) + 1
                results.append(res)
            except Exception as e:
                counts["ERROR"] += 1
                results.append({"tic_id": tic, "status": f"ERROR: {str(e)}"})

            if i % 10 == 0 or i == len(targets):
                print(f"  Sector {sector}: {i}/{len(targets)}. {counts}")

    return results, counts
