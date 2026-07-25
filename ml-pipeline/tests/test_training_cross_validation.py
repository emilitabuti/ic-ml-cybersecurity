from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.training.cross_validation import make_stratified_kfold
from src.training.data_preparation import prepare_windowed_binary_arrays
from src.training.train_dt import train_decision_tree
from src.training.train_rf import train_random_forest


def _small_prepared_dataset():
    rng = np.random.default_rng(config.RANDOM_SEED)
    X = rng.normal(size=(80, 4))
    y = np.array([0, 1] * 40)
    attack_types = np.where(y == 1, "DDoS", "BENIGN")
    return prepare_windowed_binary_arrays(
        X=X,
        y=y,
        attack_types=attack_types,
        window_size=5,
    )


def test_rf_and_dt_share_same_kfold_splits() -> None:
    prepared = _small_prepared_dataset()
    rf_splits = list(make_stratified_kfold(n_splits=5).split(prepared.X_tabular, prepared.y))
    dt_splits = list(make_stratified_kfold(n_splits=5).split(prepared.X_tabular, prepared.y))

    for (rf_train, rf_val), (dt_train, dt_val) in zip(rf_splits, dt_splits):
        np.testing.assert_array_equal(rf_train, dt_train)
        np.testing.assert_array_equal(rf_val, dt_val)


def test_train_random_forest_reports_five_fold_metrics(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(config, "RF_N_ESTIMATORS", 5)
    prepared = _small_prepared_dataset()

    result = train_random_forest(
        prepared=prepared,
        use_mlflow=False,
        n_splits=5,
        output_dir=str(tmp_path),
    )

    assert result.n_splits == 5
    assert len(result.fold_metrics) == 5
    assert result.result_path and result.result_path.exists()
    assert result.predictions_path and result.predictions_path.exists()
    predictions = pd.read_csv(result.predictions_path)
    assert {"fold", "y_true", "y_pred", "y_score", "attack_type"}.issubset(predictions.columns)


def test_train_decision_tree_uses_project_seed_and_experiment_name(tmp_path: Path) -> None:
    prepared = _small_prepared_dataset()

    result = train_decision_tree(
        prepared=prepared,
        use_mlflow=False,
        n_splits=5,
        output_dir=str(tmp_path),
    )

    assert result.model_type == "decision_tree"
    assert result.random_state == config.RANDOM_SEED
    assert len(result.fold_metrics) == 5
