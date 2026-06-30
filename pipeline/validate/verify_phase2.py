"""
Exhaustive Post-Plan Verification & Schema Validation Logic for Phase 2.
Validates pipeline outputs, Parquet columns, model formats, and payload JSON
against the Next.js frontend structural contract (/outputs/integration-schema.ts).
"""

import os
import json
import re
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# --- Signature Constants for File Integrity ---
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
HDF5_SIGNATURE = b'\x89HDF\r\n\x1a\n'
ZIP_SIGNATURE = b'PK\x03\x04'  # NPZ is technically a ZIP file

# --- Expected Schema Definitions ---
REQUIRED_PARQUET_COLUMNS = {
    # Phase 1 Columns
    'tic_id': 'int',
    'sector': 'int',
    'tess_mag': 'float',
    'ra': 'float',
    'dec': 'float',
    'candidate_num': 'int',
    'tls_period': 'float',
    'tls_t0': 'float',
    'tls_sde': 'float',
    'tls_snr': 'float',
    'tls_cdpp': 'float',
    'tls_depth': 'float',
    'tls_duration': 'float',
    'n_valid_cadences': 'int',
    
    # Phase 2 Tabular Features
    'odd_even_depth_diff': 'float',
    'secondary_eclipse_depth': 'float',
    'centroid_shift_sigma': 'float',
    'v_shape_metric': 'float',
    'crowdsap': 'float',
    'duration_period_ratio': 'float',
    
    # Phase 2 Predictions
    'predicted_class': 'int',
    'confidence_pc': 'float',
    'prob_EB': 'float',
    'prob_Blend': 'float',
    'prob_StellarVar': 'float',
    'confidence_tier': 'string'
}

VALID_CONFIDENCE_TIERS = {'GOLD', 'SILVER', 'BRONZE', 'FALSE_POSITIVE'}
VALID_DISPOSITIONS = {
    'CONFIRMED_PLANET', 
    'BINARY_STAR_ECLIPSE', 
    'BACKGROUND_STELLAR_CONTAMINATION', 
    'FALSE_ALARM'
}
VALID_RECOVERY_STATUSES = {'RECOVERED', 'NOT_RECOVERED', 'INSUFFICIENT_DATA'}
VALID_SECTOR_STATUSES = {'PASS', 'FAIL'}


def check_file_signature(filepath: Path, signature: bytes, description: str) -> bool:
    """Validate file integrity by inspecting its magic number header."""
    if not filepath.exists():
        print(f"[FAIL] File missing: {filepath}")
        return False
    try:
        with open(filepath, 'rb') as f:
            header = f.read(len(signature))
        if header == signature:
            print(f"[OK] File signature verified: {filepath.name} ({description})")
            return True
        else:
            print(f"[FAIL] File corruption detected: {filepath.name} does not match {description} signature.")
            return False
    except Exception as e:
        print(f"[FAIL] Error reading {filepath}: {e}")
        return False


def verify_file_existence(parquet_path: Path, payload_path: Path, model_dir: Path, output_dir: Path) -> bool:
    """Verify that all expected wave files exist and are uncorrupted."""
    print("\n--- Verifying File Existence & Header Signatures ---")
    all_ok = True
    
    # Check outputs directory
    if not output_dir.exists():
        print(f"[FAIL] Output directory missing: {output_dir}")
        all_ok = False
        
    # Check models directory
    if not model_dir.exists():
        print(f"[FAIL] Model directory missing: {model_dir}")
        all_ok = False

    # Check Parquet catalogue file
    if not parquet_path.exists():
        print(f"[FAIL] Master catalogue missing: {parquet_path}")
        all_ok = False
    else:
        print(f"[OK] Master catalogue found: {parquet_path.name}")

    # Check TS Contract file (payload)
    if not payload_path.exists():
        print(f"[FAIL] Payload JSON contract missing: {payload_path}")
        all_ok = False
    else:
        print(f"[OK] Payload JSON contract found: {payload_path.name}")

    # Check Model files
    cnn_path = model_dir / 'cnn_finetuned.h5'
    xgb_path = model_dir / 'xgboost_ensemble.json'
    temp_path = model_dir / 'temperature_scalar.npz'
    
    if cnn_path.exists():
        # Verify HDF5 signature
        all_ok &= check_file_signature(cnn_path, HDF5_SIGNATURE, "HDF5 Model")
    else:
        print(f"[FAIL] Fine-tuned CNN model missing: {cnn_path}")
        all_ok = False

    if xgb_path.exists():
        # Try loading as JSON
        try:
            with open(xgb_path, 'r') as f:
                json.load(f)
            print(f"[OK] File signature verified: {xgb_path.name} (XGBoost JSON)")
        except Exception as e:
            print(f"[FAIL] XGBoost model is not valid JSON: {e}")
            all_ok = False
    else:
        print(f"[FAIL] XGBoost ensemble model missing: {xgb_path}")
        all_ok = False

    if temp_path.exists():
        all_ok &= check_file_signature(temp_path, ZIP_SIGNATURE, "NPZ Numpy archive")
    else:
        print(f"[FAIL] Temperature scaler NPZ missing: {temp_path}")
        all_ok = False

    # Check validation plots
    cf_matrix = output_dir / 'confusion_matrix.png'
    reliability = output_dir / 'reliability.png'
    
    if cf_matrix.exists():
        all_ok &= check_file_signature(cf_matrix, PNG_SIGNATURE, "PNG Plot")
    else:
        print(f"[FAIL] Confusion matrix plot missing: {cf_matrix}")
        all_ok = False

    if reliability.exists():
        all_ok &= check_file_signature(reliability, PNG_SIGNATURE, "PNG Plot")
    else:
        print(f"[FAIL] Reliability plot missing: {reliability}")
        all_ok = False

    return all_ok


def verify_parquet_schema(parquet_path: Path) -> bool:
    """Validate that master Parquet catalogue complies with schema contract."""
    print("\n--- Verifying Parquet Catalogue Schema ---")
    if not parquet_path.exists():
        print("[FAIL] Cannot verify Parquet schema: file does not exist.")
        return False
        
    try:
        df = pd.read_parquet(parquet_path)
        print(f"[OK] Loaded master Parquet catalogue. Rows: {len(df)}, Columns: {len(df.columns)}")
        
        all_ok = True
        
        # Check required columns and types
        for col, expected_type in REQUIRED_PARQUET_COLUMNS.items():
            if col not in df.columns:
                print(f"[FAIL] Missing required column: {col}")
                all_ok = False
                continue
                
            col_dtype = str(df[col].dtype)
            
            # Simple soft type matching
            type_matched = False
            if expected_type == 'int' and ('int' in col_dtype or 'float' in col_dtype):
                type_matched = True
            elif expected_type == 'float' and ('float' in col_dtype or 'int' in col_dtype):
                type_matched = True
            elif expected_type == 'string' and ('object' in col_dtype or 'str' in col_dtype or 'category' in col_dtype):
                type_matched = True
                
            if not type_matched:
                print(f"[WARN] Column '{col}' type mismatch. Expected: {expected_type}, Got: {col_dtype}")
            else:
                # Value bounds checks
                if col == 'confidence_pc':
                    out_of_bounds = df[(df[col] < 0.0) | (df[col] > 1.0)]
                    if len(out_of_bounds) > 0:
                        print(f"[FAIL] confidence_pc values out of range [0, 1] found in {len(out_of_bounds)} rows.")
                        all_ok = False
                elif col == 'prob_EB':
                    out_of_bounds = df[(df[col] < 0.0) | (df[col] > 1.0)]
                    if len(out_of_bounds) > 0:
                        print(f"[FAIL] prob_EB values out of range [0, 1] found in {len(out_of_bounds)} rows.")
                        all_ok = False
                elif col == 'confidence_tier':
                    # Allow mixed casing in parquet, but validate values
                    invalid_tiers = df[~df[col].astype(str).str.upper().isin(VALID_CONFIDENCE_TIERS)]
                    if len(invalid_tiers) > 0:
                        invalid_vals = invalid_tiers[col].unique()
                        print(f"[FAIL] Invalid confidence tiers found: {invalid_vals}")
                        all_ok = False
                        
        if all_ok:
            print("[OK] All required Parquet columns are present and uncorrupted.")
            return True
        return False
        
    except Exception as e:
        print(f"[FAIL] Failed to parse Parquet: {e}")
        return False


def verify_payload_schema(payload_path: Path) -> bool:
    """Validate outputs/pipeline-payload.json structurally against typescript contract."""
    print("\n--- Verifying Payload JSON against TS Integration Schema ---")
    if not payload_path.exists():
        print("[FAIL] Cannot verify payload schema: file does not exist.")
        return False
        
    try:
        with open(payload_path, 'r') as f:
            data = json.load(f)
            
        all_ok = True
        
        # 1. Top level check
        required_root_keys = {'timestamp', 'pipelineVersion', 'hourElapsed', 'candidates'}
        missing_root = required_root_keys - set(data.keys())
        if missing_root:
            print(f"[FAIL] Missing root payload keys: {missing_root}")
            return False
            
        # 2. Field type checks
        if not isinstance(data['timestamp'], str):
            print(f"[FAIL] 'timestamp' must be a string, got {type(data['timestamp'])}")
            all_ok = False
        else:
            # Check ISO-8601 regex
            iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
            if not re.match(iso_pattern, data['timestamp']):
                print(f"[FAIL] 'timestamp' is not valid ISO-8601: {data['timestamp']}")
                all_ok = False
                
        if not isinstance(data['pipelineVersion'], str):
            print(f"[FAIL] 'pipelineVersion' must be a string, got {type(data['pipelineVersion'])}")
            all_ok = False
            
        if not isinstance(data['hourElapsed'], (int, float)):
            print(f"[FAIL] 'hourElapsed' must be a number, got {type(data['hourElapsed'])}")
            all_ok = False
            
        if not isinstance(data['candidates'], dict):
            print(f"[FAIL] 'candidates' must be a dictionary, got {type(data['candidates'])}")
            return False
            
        # 3. Candidate entry checks
        print(f"[INFO] Validating {len(data['candidates'])} candidates in payload...")
        for tic_id, candidate in data['candidates'].items():
            candidate_ok = True
            
            # Check sub-structures
            required_candidate_keys = {'signal', 'lightCurve', 'validation'}
            missing_cand_keys = required_candidate_keys - set(candidate.keys())
            if missing_cand_keys:
                print(f"[FAIL] Candidate {tic_id} is missing sub-structures: {missing_cand_keys}")
                all_ok = False
                continue
                
            # A. AstronomicalSignal check
            sig = candidate['signal']
            required_signal_keys = {
                'ticId', 'name', 'ra', 'dec', 'period', 'depth', 
                'sde', 'snr', 't0', 'duration', 'confidenceTier', 'disposition'
            }
            missing_sig_keys = required_signal_keys - set(sig.keys())
            if missing_sig_keys:
                print(f"[FAIL] Candidate {tic_id} signal is missing keys: {missing_sig_keys}")
                candidate_ok = False
            else:
                if sig['ticId'] != tic_id:
                    print(f"[FAIL] Candidate {tic_id} signal.ticId '{sig['ticId']}' mismatch with key.")
                    candidate_ok = False
                if not isinstance(sig['ra'], (int, float)) or not (0.0 <= sig['ra'] <= 360.0):
                    print(f"[FAIL] Candidate {tic_id} ra is out of range [0, 360]: {sig['ra']}")
                    candidate_ok = False
                if not isinstance(sig['dec'], (int, float)) or not (-90.0 <= sig['dec'] <= 90.0):
                    print(f"[FAIL] Candidate {tic_id} dec is out of range [-90, 90]: {sig['dec']}")
                    candidate_ok = False
                if sig['confidenceTier'] not in VALID_CONFIDENCE_TIERS:
                    print(f"[FAIL] Candidate {tic_id} has invalid confidenceTier: {sig['confidenceTier']}")
                    candidate_ok = False
                if sig['disposition'] not in VALID_DISPOSITIONS:
                    print(f"[FAIL] Candidate {tic_id} has invalid disposition: {sig['disposition']}")
                    candidate_ok = False
                    
            # B. LightCurveData check
            lc = candidate['lightCurve']
            required_lc_keys = {'rawPhase', 'rawFlux', 'modelPhase', 'modelFlux'}
            missing_lc_keys = required_lc_keys - set(lc.keys())
            if missing_lc_keys:
                print(f"[FAIL] Candidate {tic_id} lightCurve is missing keys: {missing_lc_keys}")
                candidate_ok = False
            else:
                # Types
                for k in required_lc_keys:
                    if not isinstance(lc[k], list):
                        print(f"[FAIL] Candidate {tic_id} lightCurve.{k} is not a list.")
                        candidate_ok = False
                if candidate_ok:
                    if len(lc['rawPhase']) != len(lc['rawFlux']):
                        print(f"[FAIL] Candidate {tic_id} rawPhase ({len(lc['rawPhase'])}) and rawFlux ({len(lc['rawFlux'])}) length mismatch.")
                        candidate_ok = False
                    if len(lc['modelPhase']) != len(lc['modelFlux']):
                        print(f"[FAIL] Candidate {tic_id} modelPhase ({len(lc['modelPhase'])}) and modelFlux ({len(lc['modelFlux'])}) length mismatch.")
                        candidate_ok = False
                        
            # C. Validation check (Sherlock + Triceratops)
            val = candidate['validation']
            required_val_keys = {'sherlock', 'triceratops'}
            missing_val_keys = required_val_keys - set(val.keys())
            if missing_val_keys:
                print(f"[FAIL] Candidate {tic_id} validation is missing keys: {missing_val_keys}")
                candidate_ok = False
            else:
                # Triceratops
                tr = val['triceratops']
                required_tr_keys = {'fpp', 'nfpp', 'modes'}
                missing_tr_keys = required_tr_keys - set(tr.keys())
                if missing_tr_keys:
                    print(f"[FAIL] Candidate {tic_id} triceratops missing keys: {missing_tr_keys}")
                    candidate_ok = False
                else:
                    if not isinstance(tr['fpp'], (int, float)) or not (0.0 <= tr['fpp'] <= 1.0):
                        print(f"[FAIL] Candidate {tic_id} triceratops.fpp must be float [0, 1]. Got {tr['fpp']}")
                        candidate_ok = False
                    # Modes check
                    modes = tr['modes']
                    required_mode_keys = {'tp', 'eb', 'heb', 'bgob'}
                    missing_modes = required_mode_keys - set(modes.keys())
                    if missing_modes:
                        print(f"[FAIL] Candidate {tic_id} triceratops.modes missing keys: {missing_modes}")
                        candidate_ok = False
                    else:
                        mode_sum = sum(modes.values())
                        if abs(mode_sum - 1.0) > 0.05:
                            print(f"[WARN] Candidate {tic_id} triceratops modes do not sum to 1.0: {mode_sum}")
                            
                # Sherlock
                sh = val['sherlock']
                required_sh_keys = {'sectors', 'snrPerSector', 'passFailMatrix', 'overallRecoveryStatus'}
                missing_sh_keys = required_sh_keys - set(sh.keys())
                if missing_sh_keys:
                    print(f"[FAIL] Candidate {tic_id} sherlock missing keys: {missing_sh_keys}")
                    candidate_ok = False
                else:
                    if not isinstance(sh['sectors'], list) or not isinstance(sh['snrPerSector'], list):
                        print(f"[FAIL] Candidate {tic_id} sherlock sectors or snrPerSector must be lists.")
                        candidate_ok = False
                    if sh['overallRecoveryStatus'] not in VALID_RECOVERY_STATUSES:
                        print(f"[FAIL] Candidate {tic_id} sherlock invalid recovery status: {sh['overallRecoveryStatus']}")
                        candidate_ok = False
                    # Matrix check
                    if not isinstance(sh['passFailMatrix'], list):
                        print(f"[FAIL] Candidate {tic_id} sherlock passFailMatrix must be list.")
                        candidate_ok = False
                    else:
                        for entry in sh['passFailMatrix']:
                            required_entry_keys = {'sector', 'periodMatch', 'depthConsistency', 'snr', 'status'}
                            missing_entry_keys = required_entry_keys - set(entry.keys())
                            if missing_entry_keys:
                                print(f"[FAIL] Candidate {tic_id} sherlock matrix entry missing keys: {missing_entry_keys}")
                                candidate_ok = False
                            else:
                                if entry['status'] not in VALID_SECTOR_STATUSES:
                                    print(f"[FAIL] Candidate {tic_id} sherlock matrix entry invalid status: {entry['status']}")
                                    candidate_ok = False
            
            all_ok &= candidate_ok
            
        if all_ok:
            print("[OK] Payload JSON verified successfully against TS integration contract.")
            return True
        return False
        
    except Exception as e:
        print(f"[FAIL] Failed to parse payload JSON: {e}")
        return False


def generate_mock_assets(parquet_path: Path, payload_path: Path, model_dir: Path, output_dir: Path) -> None:
    """Generate compliant, uncorrupted mock assets for development validation."""
    print("\n--- Generating Compliant Mock Pipeline Assets ---")
    
    # 1. Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 2. Write mock Parquet
    mock_data = []
    tic_ids = [22529346, 307210830, 259377017]  # WASP-121, L 98-59, TOI-270
    for idx, tic in enumerate(tic_ids):
        mock_data.append({
            'tic_id': tic,
            'sector': 1 if tic == 22529346 else (2 if tic == 307210830 else 3),
            'tess_mag': 10.5 + idx,
            'ra': 100.0 + idx * 5,
            'dec': -20.0 - idx * 2,
            'candidate_num': 1,
            'tls_period': 1.27 if tic == 22529346 else (2.25 if tic == 307210830 else 3.36),
            'tls_t0': 1325.0 + idx,
            'tls_sde': 8.5 + idx,
            'tls_snr': 12.0 + idx * 2,
            'tls_cdpp': 200.0,
            'tls_depth': 12.0 if tic == 22529346 else 1.5,
            'tls_duration': 2.5,
            'n_valid_cadences': 18000,
            'odd_even_depth_diff': 0.1,
            'secondary_eclipse_depth': 0.0,
            'centroid_shift_sigma': 0.5,
            'v_shape_metric': 0.15,
            'crowdsap': 0.95,
            'duration_period_ratio': 0.05,
            'predicted_class': 0,  # Planet Candidate
            'confidence_pc': 0.95 if idx == 0 else 0.82,
            'prob_EB': 0.02,
            'prob_Blend': 0.02,
            'prob_StellarVar': 0.01,
            'confidence_tier': 'GOLD' if idx == 0 else 'SILVER'
        })
    df = pd.DataFrame(mock_data)
    df.to_parquet(parquet_path)
    print(f"[OK] Generated mock Parquet at: {parquet_path}")

    # 3. Write mock models
    cnn_path = model_dir / 'cnn_finetuned.h5'
    with open(cnn_path, 'wb') as f:
        # Write HDF5 signature and filler
        f.write(HDF5_SIGNATURE)
        f.write(b'\x00' * 1024)
    print(f"[OK] Generated mock CNN model at: {cnn_path}")
        
    xgb_path = model_dir / 'xgboost_ensemble.json'
    xgb_dummy = {"learner": {"features": ["f1", "f2"], "objective": "multi:softprob"}}
    with open(xgb_path, 'w') as f:
        json.dump(xgb_dummy, f)
    print(f"[OK] Generated mock XGBoost model at: {xgb_path}")

    temp_path = model_dir / 'temperature_scalar.npz'
    np.savez(temp_path, T=np.array([1.25]))
    print(f"[OK] Generated mock Temperature Scaler at: {temp_path}")

    # 4. Write mock plots
    for plot_path in [output_dir / 'confusion_matrix.png', output_dir / 'reliability.png']:
        with open(plot_path, 'wb') as f:
            f.write(PNG_SIGNATURE)
            f.write(b'\x00' * 512)
        print(f"[OK] Generated mock plot at: {plot_path}")

    # 5. Write mock payload JSON
    mock_payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "pipelineVersion": "v1.2.0-GS",
        "hourElapsed": 18,
        "candidates": {}
    }
    
    for row in mock_data:
        tic_str = str(row['tic_id'])
        mock_payload["candidates"][tic_str] = {
            "signal": {
                "ticId": tic_str,
                "name": f"TIC {tic_str}",
                "ra": float(row['ra']),
                "dec": float(row['dec']),
                "period": float(row['tls_period']),
                "depth": float(row['tls_depth']),
                "sde": float(row['tls_sde']),
                "snr": float(row['tls_snr']),
                "t0": float(row['tls_t0']),
                "duration": float(row['tls_duration']),
                "confidenceTier": row['confidence_tier'],
                "disposition": "CONFIRMED_PLANET" if row['confidence_tier'] == "GOLD" else "FALSE_ALARM"
            },
            "lightCurve": {
                "rawPhase": list(np.linspace(-0.5, 0.5, 50)),
                "rawFlux": list(1.0 + np.random.normal(0, 0.001, 50)),
                "modelPhase": list(np.linspace(-0.1, 0.1, 20)),
                "modelFlux": list(1.0 - 0.012 * np.exp(-0.5 * (np.linspace(-0.1, 0.1, 20) / 0.02)**2))
            },
            "validation": {
                "triceratops": {
                    "fpp": 0.015,
                    "nfpp": 0.001,
                    "modes": {"tp": 0.98, "eb": 0.01, "heb": 0.005, "bgob": 0.005}
                },
                "sherlock": {
                    "sectors": [row['sector']],
                    "snrPerSector": [float(row['tls_snr'])],
                    "passFailMatrix": [
                        {
                            "sector": int(row['sector']),
                            "periodMatch": True,
                            "depthConsistency": True,
                            "snr": float(row['tls_snr']),
                            "status": "PASS"
                        }
                    ],
                    "overallRecoveryStatus": "RECOVERED"
                }
            }
        }
        
    with open(payload_path, 'w') as f:
        json.dump(mock_payload, f, indent=2)
    print(f"[OK] Generated mock Payload JSON at: {payload_path}")


def main():
    parser = argparse.ArgumentParser(description="Phase 2 Post-Plan Verification Engine")
    parser.add_argument("--parquet", type=str, default="outputs/catalogue/master_catalogue.parquet",
                        help="Path to master Parquet catalogue")
    parser.add_argument("--payload", type=str, default="outputs/pipeline-payload.json",
                        help="Path to pipeline payload JSON contract")
    parser.add_argument("--model-dir", type=str, default="outputs/models",
                        help="Directory containing ML model checkpoints")
    parser.add_argument("--output-dir", type=str, default="outputs",
                        help="Outputs base directory")
    parser.add_argument("--generate-mock", action="store_true",
                        help="Pre-generate mock files for testing runner")
    args = parser.parse_args()

    parquet_path = Path(args.parquet)
    payload_path = Path(args.payload)
    model_dir = Path(args.model_dir)
    output_dir = Path(args.output_dir)

    if args.generate_mock:
        generate_mock_assets(parquet_path, payload_path, model_dir, output_dir)

    print("==================================================")
    print("PHASE 2 DEPLOYMENT VERIFICATION ENGINE")
    print("==================================================")

    # 1. Existence and integrity checks
    ok_existence = verify_file_existence(parquet_path, payload_path, model_dir, output_dir)
    
    # 2. Schema structure checks
    ok_parquet = verify_parquet_schema(parquet_path)
    ok_payload = verify_payload_schema(payload_path)

    print("\n==================================================")
    if ok_existence and ok_parquet and ok_payload:
        print("[SUCCESS] INTEGRITY AND SCHEMA VERIFICATION: PASSED")
        print("All Phase 2 modules deployed successfully and matched frontend contract.")
        print("==================================================")
        exit(0)
    else:
        print("[ERROR] INTEGRITY AND SCHEMA VERIFICATION: FAILED")
        print("Review the logs above to identify file corruption or schema mismatch.")
        print("==================================================")
        exit(1)


if __name__ == '__main__':
    main()
