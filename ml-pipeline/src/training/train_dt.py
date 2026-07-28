"""Treino Decision Tree com k-fold e rastreamento MLflow."""
from __future__ import annotations

import argparse

from sklearn.tree import DecisionTreeClassifier

import config
from src.training.cross_validation import ExperimentResult, run_sklearn_cross_validation
from src.training.data_preparation import PreparedDataset, prepare_windowed_binary_dataset
from src.training.metrics import METRIC_NAMES, format_mean_std
from src.utils.seed import set_global_seed


def build_decision_tree(**overrides: object) -> DecisionTreeClassifier:
    """Cria DecisionTreeClassifier com o mesmo seed/split do RF."""
    params: dict[str, object] = {
        "max_depth": _optional_int(config.DT_MAX_DEPTH),
        "random_state": config.RANDOM_SEED,
    }
    params.update({key: value for key, value in overrides.items() if value is not None})
    return DecisionTreeClassifier(**params)


def train_decision_tree(
    prepared: PreparedDataset | None = None,
    use_mlflow: bool = True,
    n_splits: int | None = None,
    output_dir: str | None = None,
) -> ExperimentResult:
    """Executa k-fold k=5 do DT nas mesmas condições do RF."""
    set_global_seed(config.RANDOM_SEED)
    dataset = prepared or prepare_windowed_binary_dataset()
    hyperparameters = build_decision_tree().get_params()
    return run_sklearn_cross_validation(
        estimator_factory=build_decision_tree,
        prepared=dataset,
        model_type="decision_tree",
        algorithm="DecisionTreeClassifier",
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

    print("[DT] Carregando e preparando dataset (pode levar alguns segundos)...", flush=True)
    prepared = prepare_windowed_binary_dataset(dataset=args.dataset)
    print(
        f"[DT] Dataset pronto: X_tabular={prepared.X_tabular.shape}, y={prepared.y.shape}",
        flush=True,
    )
    result = train_decision_tree(
        prepared=prepared,
        use_mlflow=not args.no_mlflow,
        output_dir=args.output_dir,
    )
    _print_summary(result)


def _print_summary(result: ExperimentResult) -> None:
    print("Decision Tree k-fold concluido")
    for metric_name in METRIC_NAMES:
        print(f"{metric_name}: {format_mean_std(result.summary[metric_name])}")


def _optional_int(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


if __name__ == "__main__":
    main()
