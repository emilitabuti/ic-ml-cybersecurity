"""Treino Random Forest com k-fold e rastreamento MLflow."""
from __future__ import annotations

import argparse

from sklearn.ensemble import RandomForestClassifier

import config
from src.training.cross_validation import ExperimentResult, run_sklearn_cross_validation
from src.training.data_preparation import PreparedDataset, prepare_windowed_binary_dataset
from src.training.metrics import METRIC_NAMES, format_mean_std
from src.utils.seed import set_global_seed


def build_random_forest(**overrides: object) -> RandomForestClassifier:
    """Cria RandomForestClassifier com seed científico do projeto."""
    params: dict[str, object] = {
        "n_estimators": config.RF_N_ESTIMATORS,
        "max_depth": _optional_int(config.RF_MAX_DEPTH),
        "random_state": config.RANDOM_SEED,
        "n_jobs": config.RF_N_JOBS,
        "verbose": 1,
    }
    params.update({key: value for key, value in overrides.items() if value is not None})
    return RandomForestClassifier(**params)


def train_random_forest(
    prepared: PreparedDataset | None = None,
    use_mlflow: bool = True,
    n_splits: int | None = None,
    output_dir: str | None = None,
) -> ExperimentResult:
    """Executa k-fold k=5 do RF com o mesmo seed dos demais modelos."""
    set_global_seed(config.RANDOM_SEED)
    dataset = prepared or prepare_windowed_binary_dataset()
    hyperparameters = build_random_forest().get_params()
    return run_sklearn_cross_validation(
        estimator_factory=build_random_forest,
        prepared=dataset,
        model_type="random_forest",
        algorithm="RandomForestClassifier",
        hyperparameters=hyperparameters,
        n_splits=n_splits,
        random_state=config.RANDOM_SEED,
        use_mlflow=use_mlflow,
        output_dir=output_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="cic", choices=["cic", "unsw"])
    parser.add_argument("--no-mlflow", action="store_true")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    print("[RF] Carregando e preparando dataset (pode levar alguns segundos)...", flush=True)
    prepared = prepare_windowed_binary_dataset(dataset=args.dataset)
    print(
        f"[RF] Dataset pronto: X_tabular={prepared.X_tabular.shape}, y={prepared.y.shape}",
        flush=True,
    )
    result = train_random_forest(
        prepared=prepared,
        use_mlflow=not args.no_mlflow,
        output_dir=args.output_dir,
    )
    _print_summary(result)


def _print_summary(result: ExperimentResult) -> None:
    print("Random Forest k-fold concluido")
    for metric_name in METRIC_NAMES:
        print(f"{metric_name}: {format_mean_std(result.summary[metric_name])}")


def _optional_int(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


if __name__ == "__main__":
    main()
