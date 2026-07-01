import numpy as np

def apply_gap_mask(time, gap_threshold=0.1, edge_days=0.5):
    """
    Detect gaps (TESS downlink etc.) in the time series.
    Returns a boolean mask where True means the cadence is near a gap edge (unreliable),
    and a list of gap start/end times.
    """
    if len(time) <= 1:
        return np.zeros(len(time), dtype=bool), []
        
    diffs = np.diff(time)
    gap_idx = np.where(diffs > gap_threshold)[0]
    
    gaps = []
    gap_mask = np.zeros(len(time), dtype=bool)
    
    for idx in gap_idx:
        t_start = time[idx]
        t_end = time[idx + 1]
        gaps.append((float(t_start), float(t_end)))
        
        # Flag points within edge_days of the gap start/end
        near_gap = (time >= t_start - edge_days) & (time <= t_end + edge_days)
        gap_mask = gap_mask | near_gap
        
    return gap_mask, gaps
