import pandas as pd
from pathlib import Path

# Mapping system names to their TIC IDs and explicit lists of expected planet periods (7 total targets)
BENCHMARKS = {
    "WASP-121b": {"tic_id": 22529346, "periods": [1.27492]},
    "L 98-59": {"tic_id": 307210830, "periods": [2.25311, 3.69068, 7.45073]},  # planets b, c, d
    "TOI-270": {"tic_id": 259377017, "periods": [3.36008, 5.66017, 11.38014]}  # planets b, c, d
}

def run_smoke_test(catalogue_path):
    """
    Validate recovery of all 7 known benchmark planets across the 3 systems.
    """
    path = Path(catalogue_path)
    if not path.exists():
        print(f"Warning: Catalogue not found at {catalogue_path}.")
        return False
        
    all_passed = True
    try:
        df = pd.read_parquet(path)
        
        for system, info in BENCHMARKS.items():
            # Filter the dataframe for this specific star system
            star_signals = df[df['tic_id'] == info['tic_id']]
            
            for expected_p in info['periods']:
                match_found = False
                
                # Check if any recovered row in the dataframe matches this specific period
                for _, row in star_signals.iterrows():
                    diff = abs(row['period'] - expected_p) / expected_p
                    if diff < 0.01 and row.get('disposition') != 'DISCARD':
                        match_found = True
                        break
                
                if not match_found:
                    print(f"❌ Verification FAILED: {system} planet with period {expected_p}d not found.")
                    all_passed = False
                else:
                    print(f"✅ Verified: {system} planet with period {expected_p}d recovered.")
                        
    except Exception as e:
        print(f"Error during smoke test validation: {e}")
        return False
        
    return all_passed
