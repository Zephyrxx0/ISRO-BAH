def get_exclusion_reason(tmag, n_cadences):
    """
    Check if a star should be excluded from processing based on:
    - Saturated/very bright stars (Tmag < 6)
    - Too few valid data points (< 500 cadences)
    """
    import math
    if tmag is not None and not math.isnan(tmag) and tmag < 6.0:
        return "SATURATED"
    if n_cadences < 500:
        return "TOO_FEW_CADENCES"
    return "NONE"

def should_process(tmag, n_cadences):
    """Return True if the star passes the exclusion filters."""
    return get_exclusion_reason(tmag, n_cadences) == "NONE"
