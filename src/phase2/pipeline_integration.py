"""Phase 2 pipeline orchestrator — wires all steps into run_pipeline.py.

This module handles inference and feature extraction only.
Training scripts (train_cnn_finetune.py, train_xgboost.py) are standalone
and must be run manually before this orchestrator.

Usage from run_pipeline.py:
    from src.phase2.pipeline_integration import run_phase2
    run_phase2('data/catalogue/master.parquet', sectors=[1, 2, 3])
"""

from pathlib import Path

from src.phase2.validate_phase1 import validate_phase1_outputs
from src.phase2.phase_folder import PhaseFolder
from src.phase2.feature_extractor import FeatureExtractor
from src.phase2.centroid_analyzer import CentroidAnalyzer
from src.phase2.ensemble_predictor import EnsemblePredictor


def run_phase2(catalogue_path: str, sectors: list,
               model_dir: str = 'data/models') -> None:
    """Execute Phase 2: Feature Engineering & Classification.

    This is the inference-only orchestrator. Training scripts must be run
    separately before this function (see docs/adr/0004-kepler-pretrain.md).

    Steps:
        1. Validate Phase 1 outputs (catalogue schema + .npz file integrity)
        2. Phase-fold all SDE>=5 candidates (2001 global + 201 local views)
        3. Extract engineered features (8 features → master Parquet)
        4. Run centroid analysis on top 200 SDE>=7 candidates
        5. Run ensemble classification (requires pre-trained model artifacts)

    Args:
        catalogue_path: Path to master.parquet.
        sectors: List of sector numbers (e.g., [1, 2, 3]).
        model_dir: Directory containing trained model artifacts:
                   - cnn_finetuned.h5
                   - xgboost_ensemble.json
                   - temperature_scalar.npz
    """
    print('=' * 60)
    print('PHASE 2: Intelligence — Feature Engineering & Classification')
    print(f'Sectors: {sectors}')
    print(f'Model directory: {model_dir}')
    print('=' * 60)

    # Step 1: Validate Phase 1 outputs
    print('\n[Step 1/5] Validating Phase 1 outputs...')
    validate_phase1_outputs(catalogue_path)

    # Step 2: Phase-fold all SDE>=5 candidates
    print('\n[Step 2/5] Phase-folding candidates...')
    preprocessed_dir = 'data/preprocessed'
    folded_dir = 'data/folded'
    folder = PhaseFolder(catalogue_path, preprocessed_dir, folded_dir)
    folder.run_all()

    # Step 3: Extract engineered features
    print('\n[Step 3/5] Extracting features...')
    extractor = FeatureExtractor(catalogue_path, preprocessed_dir, folded_dir)
    extractor.run_all()

    # Step 4: Centroid analysis on top 200 SDE>=7
    print('\n[Step 4/5] Running centroid analysis (top 200)...')
    analyzer = CentroidAnalyzer(catalogue_path, tpf_cache_dir='data/tpf', top_n=200)
    analyzer.run_top_n()

    # Step 5: Ensemble classification
    print('\n[Step 5/5] Running ensemble classification...')
    cnn_path = str(Path(model_dir) / 'cnn_finetuned.h5')
    xgb_path = str(Path(model_dir) / 'xgboost_ensemble.json')
    temp_path = str(Path(model_dir) / 'temperature_scalar.npz')

    # Verify all model files exist before proceeding
    for path in [cnn_path, xgb_path, temp_path]:
        if not Path(path).exists():
            raise FileNotFoundError(
                f'Model artifact not found: {path}. '
                f'Run training scripts before pipeline inference:\n'
                f'  1. python src/phase2/train_kepler.py  (prep week)\n'
                f'  2. python src/phase2/train_cnn_finetune.py  (hackathon)\n'
                f'  3. python src/phase2/train_xgboost.py  (hackathon)'
            )

    predictor = EnsemblePredictor(cnn_path, xgb_path, temp_path)
    predictor.classify_all(catalogue_path)

    print('\n' + '=' * 60)
    print('✓ Phase 2 complete. Classification results in master Parquet.')
    print('  Next: run src/phase2/evaluate.py for E1-E10 metrics.')
    print('=' * 60)
