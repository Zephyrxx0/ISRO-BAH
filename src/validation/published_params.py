"""Published orbital parameters for validation targets.

Sources:
- WASP-121b: Delrez et al. 2016
- TOI-270 b/c/d: Günther et al. 2019, Van Eylen et al. 2021
- L 98-59 b/c/d: Kostov et al. 2019, Cadieux et al. 2025
- TOI-700 d: Gilbert et al. 2020
"""

VALIDATION_TARGETS: dict = {
    "WASP-121b": {
        "tic_id": 22529346,
        "sector": 1,
        "published": {
            "period": 1.2749255,
            "rp_rs": 0.1218,
            "depth_ppm": 14840.0,
            "duration_days": 0.1203,
            "inclination": 87.6,
            "a_rs": 3.86,
        },
        "source": "Delrez et al. 2016",
    },
    "TOI-270b": {
        "tic_id": 259377017,
        "sector": 3,
        "published": {
            "period": 3.36016,
            "rp_rs": 0.0307,
            "depth_ppm": 942.0,
            "duration_days": 0.0425,
            "inclination": 88.65,
            "a_rs": 12.09,
        },
        "source": "Günther et al. 2019",
    },
    "TOI-270c": {
        "tic_id": 259377017,
        "sector": 3,
        "published": {
            "period": 5.66057,
            "rp_rs": 0.0578,
            "depth_ppm": 3341.0,
            "duration_days": 0.0521,
            "inclination": 89.53,
            "a_rs": 17.25,
        },
        "source": "Van Eylen et al. 2021",
    },
    "TOI-270d": {
        "tic_id": 259377017,
        "sector": 3,
        "published": {
            "period": 11.38014,
            "rp_rs": 0.0535,
            "depth_ppm": 2862.0,
            "duration_days": 0.0625,
            "inclination": 89.7,
            "a_rs": 27.0,
        },
        "source": "Van Eylen et al. 2021",
    },
    "L98-59b": {
        "tic_id": 307210830,
        "sector": 2,
        "published": {
            "period": 2.2531140,
            "rp_rs": 0.0258,
            "depth_ppm": 666.0,
            "duration_days": 0.0425,
            "inclination": 87.45,
            "a_rs": 11.5,
        },
        "source": "Kostov et al. 2019",
    },
    "L98-59c": {
        "tic_id": 307210830,
        "sector": 2,
        "published": {
            "period": 3.6906764,
            "rp_rs": 0.0396,
            "depth_ppm": 1568.0,
            "duration_days": 0.0508,
            "inclination": 88.43,
            "a_rs": 15.8,
        },
        "source": "Kostov et al. 2019",
    },
    "L98-59d": {
        "tic_id": 307210830,
        "sector": 2,
        "published": {
            "period": 7.450729,
            "rp_rs": 0.0460,
            "depth_ppm": 2116.0,
            "duration_days": 0.0375,
            "inclination": 89.0,
            "a_rs": 25.0,
        },
        "source": "Cadieux et al. 2025",
    },
    "TOI-700d": {
        "tic_id": 150428135,
        "sector": 4,
        "published": {
            "period": 37.42396,
            "rp_rs": 0.015,
            "depth_ppm": 225.0,
            "duration_days": 0.166,
            "inclination": 89.7,
            "a_rs": 55.0,
        },
        "source": "Gilbert et al. 2020",
    },
}

# Tolerance thresholds for parameter recovery (PARM-06)
RECOVERY_TOLERANCES: dict = {
    "period": 0.001,      # 0.1% relative error
    "depth_ppm": 0.05,    # 5% relative error
    "duration_days": 0.10, # 10% relative error
}
