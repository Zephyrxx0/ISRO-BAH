from pathlib import Path
import os

# Base Paths (detect Kaggle environment automatically)
if os.path.exists('/kaggle/working'):
    BASE_DIR = Path('/kaggle/working')
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUTS_DIR = BASE_DIR / 'outputs'
RAW_DIR = OUTPUTS_DIR / 'raw'
PREP_DIR = OUTPUTS_DIR / 'preprocessed'
CATALOGUE_DIR = OUTPUTS_DIR / 'catalogue'

# File Paths
LD_TABLE_PATH = CATALOGUE_DIR / 'claret_ld.parquet'
MASTER_CATALOGUE_PATH = CATALOGUE_DIR / 'master_catalogue.parquet'
TLS_RESULTS_PATH = CATALOGUE_DIR / 'tls_candidates.parquet'
KEPLER_TCE_PATH = CATALOGUE_DIR / 'kepler_dr24_tce.csv'

# Default values
LD_DEFAULT = [0.3, 0.3]

# TLS search configuration
TLS_PERIOD_MIN = 0.5
TLS_PERIOD_MAX = 30.0
TLS_OVERSAMPLING = 2
TLS_ITERATIONS = 3

# SDE gating thresholds
SDE_DISCARD = 5.0
SDE_SUBTHRESHOLD = 7.0

# Dispositions
DISP_FULL_PIPELINE = "FULL_PIPELINE"
DISP_SUB_THRESHOLD = "SUB_THRESHOLD"
DISP_DISCARD = "DISCARD"
