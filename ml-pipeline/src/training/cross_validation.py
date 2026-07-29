"""Execução de k-fold cross-validation para modelos do Epic 3."""
from __future__ import annotations

from dataclasses import dataclass
import gc
import json
from pathlib import Path
from typing import Callable

import mlflow
import numpy as np
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.model_selection import StratifiedKFold

try:
    import psutil
except ModuleNotFoundError:
    psutil = None

import config
from src.training.data_preparation import PreparedDataset
from src.training.metrics import METRIC_NAMES, calculate_binary_metrics, summarize_fold_metrics
from src.training.mlflow_utils import setup_mlflow_tracking


@dataclass(frozen=True)
class ExperimentResult:
    """Resultado completo de um experimento k-fold."""

    model_type: str
    algorithm: str
    n_splits: int
    random_state: int
    window_size: int
    fold_metrics: list[dict[str, float]]
    summary: dict[str, dict[str, float]]
    result_path: Path | None
    predictions_path: Path | None
    fallback_used: bool = False


def make_stratified_kfold(
    n_splits: int | None = None,
    random_state: int | None = None,
) -> StratifiedKFold:
    """Cria o split k-fold padronizado para RF, DT e LSTM/MLP."""
    return StratifiedKFold(
        n_splits=int(n_splits or config.K_FOLDS),
        shuffle=True,
        random_state=int(random_state or config.RANDOM_SEED),
    )


def run_sklearn_cross_validation(
    estimator_factory: Callable[[], ClassifierMixin],
    prepared: PreparedDataset,
    model_type: str,
    algorithm: str,
    hyperparameters: dict[str, object],
    n_splits: int | None = None,
    random_state: int | None = None,
    use_mlflow: bool = True,
    output_dir: str | Path | None = None,
    fallback_used: bool = False,
) -> ExperimentResult:
    """Treina e avalia um estimador sklearn em k-fold com logging MLflow."""
    folds = make_stratified_kfold(n_splits=n_splits, random_state=random_state)
    resolved_random_state = int(random_state or config.RANDOM_SEED)
    resolved_n_splits = int(n_splits or config.K_FOLDS)
    output_root = Path(output_dir or config.TRAINING_REPORTS_DIR)

    if use_mlflow:
        setup_mlflow_tracking(model_type, flavor="sklearn")

    fold_metrics: list[dict[str, float]] = []
    prediction_rows: list[dict[str, object]] = []

    run_context = mlflow.start_run(run_name=f"{model_type}-kfold") if use_mlflow else _null_run()
    with run_context:
        if use_mlflow:
            _log_experiment_params(
                algorithm=algorithm,
                model_type=model_type,
                prepared=prepared,
                n_splits=resolved_n_splits,
                random_state=resolved_random_state,
                hyperparameters=hyperparameters,
                fallback_used=fallback_used,
            )

        for fold_index, (train_index, val_index) in enumerate(
            folds.split(prepared.X_tabular, prepared.y),
            start=1,
        ):
            print(
                f"[{model_type}] Fold {fold_index}/{resolved_n_splits} iniciando "
                "(o proximo log so aparece quando o fit() terminar ou, no RF, "
                "quando o joblib reportar as primeiras arvores concluidas - isso "
                "pode levar alguns minutos SEM nenhuma saida no terminal; "
                "NAO interrompa)...",
                flush=True,
            )
            log_ram_usage(f"{model_type} fold {fold_index} antes do fit")
            estimator = estimator_factory()
            # Em vez de copiar a fatia de treino/validacao (fancy-indexing sempre
            # aloca um array novo — para o UNSW-NB15 isso significa ~10.4GB so
            # para o treino, o mesmo tamanho que causou o OOM do LSTM antes do
            # fix com tf.data), treina direto no array base completo usando
            # sample_weight=0 para mascarar as linhas de validacao. Isso evita
            # qualquer copia do array gigante (~13GB) — apenas um vetor de pesos
            # (poucos MB) e alocado por fold.
            sample_weight = np.zeros(prepared.y.shape[0], dtype=np.float64)
            sample_weight[train_index] = 1.0
            estimator.fit(prepared.X_tabular, prepared.y, sample_weight=sample_weight)
            del sample_weight
            gc.collect()
            log_ram_usage(f"{model_type} fold {fold_index} depois do fit")

            # Mesma logica para a predicao: prediz no array completo (ja
            # residente em memoria, sem copia extra) e filtra o resultado (bem
            # menor: 1 valor por linha) pelas linhas de validacao.
            y_pred_all = estimator.predict(prepared.X_tabular)
            y_score_all = _predict_scores(estimator, prepared.X_tabular)
            y_true = prepared.y[val_index]
            y_pred = y_pred_all[val_index]
            y_score = y_score_all[val_index]
            del y_pred_all, y_score_all
            gc.collect()
            metrics = calculate_binary_metrics(y_true, y_pred, y_score)
            fold_metrics.append(metrics)
            print(
                f"[{model_type}] Fold {fold_index}/{resolved_n_splits} concluido: "
                f"f1={metrics['f1']:.4f} auc_roc={metrics['auc_roc']:.4f}",
                flush=True,
            )

            if use_mlflow:
                for metric_name, metric_value in metrics.items():
                    mlflow.log_metric(f"fold_{fold_index}_{metric_name}", metric_value)

            for row_index, sample_index in enumerate(val_index):
                prediction_rows.append(
                    {
                        "model_type": model_type,
                        "algorithm": algorithm,
                        "fold": fold_index,
                        "sample_index": int(sample_index),
                        "y_true": int(y_true[row_index]),
                        "y_pred": int(y_pred[row_index]),
                        "y_score": float(y_score[row_index]),
                        "attack_type": str(prepared.attack_types[sample_index]),
                    }
                )

        summary = summarize_fold_metrics(fold_metrics)
        if use_mlflow:
            for metric_name in METRIC_NAMES:
                mlflow.log_metric(f"{metric_name}_mean", summary[metric_name]["mean"])
                mlflow.log_metric(f"{metric_name}_std", summary[metric_name]["std"])

        result_path, predictions_path = _persist_results(
            output_root=output_root,
            model_type=model_type,
            algorithm=algorithm,
            n_splits=resolved_n_splits,
            random_state=resolved_random_state,
            window_size=prepared.window_size,
            hyperparameters=hyperparameters,
            fold_metrics=fold_metrics,
            summary=summary,
            prediction_rows=prediction_rows,
            fallback_used=fallback_used,
        )

    return ExperimentResult(
        model_type=model_type,
        algorithm=algorithm,
        n_splits=resolved_n_splits,
        random_state=resolved_random_state,
        window_size=prepared.window_size,
        fold_metrics=fold_metrics,
        summary=summary,
        result_path=result_path,
        predictions_path=predictions_path,
        fallback_used=fallback_used,
    )


def log_ram_usage(label: str) -> None:
    """Loga RAM disponivel/em uso (best-effort) para diagnosticar OOM em Colab."""
    if psutil is None:
        return
    vm = psutil.virtual_memory()
    process_rss_gb = psutil.Process().memory_info().rss / (1024 ** 3)
    print(
        f"[ram] {label}: processo={process_rss_gb:.2f}GB "
        f"sistema_usado={vm.percent:.0f}% "
        f"disponivel={vm.available / (1024 ** 3):.2f}GB",
        flush=True,
    )


def _predict_scores(estimator: ClassifierMixin, X: np.ndarray) -> np.ndarray:
    if hasattr(estimator, "predict_proba"):
        probabilities = estimator.predict_proba(X)
        return probabilities[:, 1] if probabilities.ndim == 2 else probabilities
    if hasattr(estimator, "decision_function"):
        scores = estimator.decision_function(X)
        return np.asarray(scores, dtype=float)
    return np.asarray(estimator.predict(X), dtype=float)


def _log_experiment_params(
    algorithm: str,
    model_type: str,
    prepared: PreparedDataset,
    n_splits: int,
    random_state: int,
    hyperparameters: dict[str, object],
    fallback_used: bool,
) -> None:
    params = {
        "algorithm": algorithm,
        "model_type": model_type,
        "WINDOW_SIZE": prepared.window_size,
        "K_FOLDS": n_splits,
        "RANDOM_SEED": random_state,
        "n_features_selected": len(prepared.feature_names),
        "fallback_used": fallback_used,
    }
    params.update(hyperparameters)
    mlflow.log_params(params)


def _persist_results(
    output_root: Path,
    model_type: str,
    algorithm: str,
    n_splits: int,
    random_state: int,
    window_size: int,
    hyperparameters: dict[str, object],
    fold_metrics: list[dict[str, float]],
    summary: dict[str, dict[str, float]],
    prediction_rows: list[dict[str, object]],
    fallback_used: bool,
) -> tuple[Path, Path]:
    metrics_dir = output_root / "metrics"
    predictions_dir = output_root / "predictions"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    predictions_dir.mkdir(parents=True, exist_ok=True)

    result_path = metrics_dir / f"{model_type}_metrics.json"
    predictions_path = predictions_dir / f"{model_type}_fold_predictions.csv"
    result_payload = {
        "model_type": model_type,
        "algorithm": algorithm,
        "n_splits": n_splits,
        "random_state": random_state,
        "window_size": window_size,
        "hyperparameters": hyperparameters,
        "fold_metrics": fold_metrics,
        "summary": summary,
        "fallback_used": fallback_used,
    }
    result_path.write_text(
        json.dumps(result_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(prediction_rows).to_csv(predictions_path, index=False)
    return result_path, predictions_path


class _null_run:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_args: object) -> None:
        return None
