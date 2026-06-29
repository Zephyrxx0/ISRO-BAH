import pandas as pd
from pathlib import Path
import pipeline.config as cfg

def apply_sde_gating(tls_results):
    """
    Applies 3-tier SDE gating to the TLS candidates list and returns a DataFrame.
    Gating tiers:
    - SDE < 5: DISCARD
    - 5 <= SDE < 7: SUB_THRESHOLD
    - SDE >= 7: FULL_PIPELINE
    """
    if not tls_results:
        # Return empty DataFrame with expected columns
        cols = ['tic_id', 'sector', 'planet_num', 'period', 't0', 'duration', 
                'depth', 'sde', 'snr', 'cdpp', 'chi2', 'chi2_red', 
                'bls_consistent', 'disposition']
        return pd.DataFrame(columns=cols)
        
    df = pd.DataFrame(tls_results)
    if 'bls_consistent' not in df.columns:
        df['bls_consistent'] = False
    else:
        df['bls_consistent'] = df['bls_consistent'].fillna(False).astype(bool)
    
    # Sort by SDE descending
    df = df.sort_values(by='sde', ascending=False).reset_index(drop=True)
    
    # Assign dispositions
    dispositions = []
    for _, row in df.iterrows():
        sde = row['sde']
        if sde < cfg.SDE_DISCARD:
            dispositions.append(cfg.DISP_DISCARD)
        elif sde < cfg.SDE_SUBTHRESHOLD:
            dispositions.append(cfg.DISP_SUB_THRESHOLD)
        else:
            dispositions.append(cfg.DISP_FULL_PIPELINE)
            
    df['disposition'] = dispositions
    return df

def save_tls_results(df):
    """Save the gated TLS search candidate table to Parquet."""
    out_path = Path(cfg.TLS_RESULTS_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    return out_path
