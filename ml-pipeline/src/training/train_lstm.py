"""Treino LSTM com k-fold e fallback MLP documentado."""
from __future__ import annotations

import argparse
import gc
import warnings

import mlflow
import numpy as np
from sklearn.neural_network import MLPClassifier

import config
from src.training.cross_validation import ExperimentResult, run_sklearn_cross_validation
from src.training.data_preparation import PreparedDataset, prepare_windowed_binary_dataset
from src.training.metrics import METRIC_NAMES, calculate_binary_metrics, format_mean_std, summarize_fold_metrics
from src.training.mlflow_utils import setup_mlflow_tracking
from src.utils.seed import set_global_seed

FALLBACK_REASON = (
    "TensorFlow nao faz parte do ambiente local padrao deste repositorio. "
    "A escolha documentada para LSTM completo e executar no Google Colab com GPU T4; "
    "quando TensorFlow nao esta disponivel localmente, este script treina MLP como "
    "fallback explicito para manter a comparacao executavel."
)


def tensorflow_available() -> bool:
    """Indica se TensorFlow pode ser importado no ambiente atual."""
    try:
        import tensorflow  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def build_mlp_fallback(**overrides: object) -> MLPClassifier:
    """Cria MLPClassifier como fallback explicito do LSTM."""
    params: dict[str, object] = {
        "hidden_layer_sizes": _parse_hidden_layers(config.MLP_HIDDEN_LAYER_SIZES),
        "max_iter": config.MLP_MAX_ITER,
        "random_state": config.RANDOM_SEED,
    }
    params.update({key: value for key, value in overrides.items() if value is not None})
    return MLPClassifier(**params)


def train_lstm_or_mlp(
    prepared: PreparedDataset | None = None,
    use_mlflow: bool = True,
    n_splits: int | None = None,
    output_dir: str | None = None,
    allow_mlp_fallback: bool = True,
) -> ExperimentResult:
    """Treina LSTM se TensorFlow existir; caso contrario usa MLP documentado."""
    set_global_seed(config.RANDOM_SEED)
    print("[LSTM] Carregando e preparando dataset (pode levar alguns segundos)...", flush=True)
    dataset = prepared or prepare_windowed_binary_dataset()
    print(
        f"[LSTM] Dataset pronto: X_sequential={dataset.X_sequential.shape}, "
        f"y={dataset.y.shape}",
        flush=True,
    )
    if tensorflow_available():
        return _run_tensorflow_lstm(
            prepared=dataset,
            use_mlflow=use_mlflow,
            n_splits=n_splits,
            output_dir=output_dir,
        )

    if not allow_mlp_fallback:
        raise RuntimeError(FALLBACK_REASON)

    warnings.warn(FALLBACK_REASON, RuntimeWarning, stacklevel=2)
    hyperparameters = build_mlp_fallback().get_params()
    return run_sklearn_cross_validation(
        estimator_factory=build_mlp_fallback,
        prepared=dataset,
        model_type="lstm",
        algorithm="MLPClassifier fallback for LSTM",
        hyperparameters=hyperparameters | {"fallback_reason": FALLBACK_REASON},
        n_splits=n_splits,
        random_state=config.RANDOM_SEED,
        use_mlflow=use_mlflow,
        output_dir=output_dir,
        fallback_used=True,
    )


def _run_tensorflow_lstm(
    prepared: PreparedDataset,
    use_mlflow: bool,
    n_splits: int | None,
    output_dir: str | None,
) -> ExperimentResult:
    import tensorflow as tf

    from src.training.cross_validation import make_stratified_kfold

    def _make_indexed_dataset(
        indices: np.ndarray, *, shuffle: bool
    ) -> "tf.data.Dataset":
        # Le uma janela por vez direto do array em memoria (view/copia minuscula,
        # ~poucos KB) em vez de materializar a fatia inteira do fold (que em
        # datasets grandes, ex.: UNSW-NB15, chega a >10GB e estoura a RAM mesmo
        # em ambientes com bastante memoria).
        def _generator():
            for sample_index in indices:
                yield prepared.X_sequential[sample_index], prepared.y[sample_index]

        dataset = tf.data.Dataset.from_generator(
            _generator,
            output_signature=(
                tf.TensorSpec(shape=prepared.X_sequential.shape[1:], dtype=tf.float32),
                tf.TensorSpec(shape=(), dtype=tf.int64),
            ),
        )
        if shuffle:
            dataset = dataset.shuffle(
                buffer_size=min(len(indices), 10_000),
                seed=config.RANDOM_SEED,
                reshuffle_each_iteration=True,
            )
        return dataset.batch(config.LSTM_BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

    tf.random.set_seed(config.RANDOM_SEED)
    folds = make_stratified_kfold(n_splits=n_splits, random_state=config.RANDOM_SEED)
    resolved_n_splits = int(n_splits or config.K_FOLDS)
    output_root = output_dir or config.TRAINING_REPORTS_DIR

    if use_mlflow:
        setup_mlflow_tracking("lstm", flavor="tensorflow")

    fold_metrics: list[dict[str, float]] = []
    prediction_rows: list[dict[str, object]] = []

    run_context = mlflow.start_run(run_name="lstm-kfold") if use_mlflow else _null_run()
    with run_context:
        if use_mlflow:
            mlflow.log_params(
                {
                    "algorithm": "TensorFlow Keras LSTM",
                    "model_type": "lstm",
                    "WINDOW_SIZE": prepared.window_size,
                    "K_FOLDS": resolved_n_splits,
                    "RANDOM_SEED": config.RANDOM_SEED,
                    "epochs": config.LSTM_EPOCHS,
                    "batch_size": config.LSTM_BATCH_SIZE,
                    "fallback_used": False,
                }
            )

        for fold_index, (train_index, val_index) in enumerate(
            folds.split(prepared.X_tabular, prepared.y),
            start=1,
        ):
            print(f"[LSTM] Fold {fold_index}/{resolved_n_splits} iniciando...", flush=True)
            # Libera o grafo/pesos do modelo do fold anterior antes de criar um novo —
            # sem isso, o Keras acumula memoria a cada fold (5x nesse pipeline), o que
            # pode ser a diferenca entre caber ou nao na RAM de ambientes limitados
            # (ex.: Colab free tier).
            tf.keras.backend.clear_session()
            gc.collect()
            tf.random.set_seed(config.RANDOM_SEED)
            y_val = prepared.y[val_index]
            train_ds = _make_indexed_dataset(train_index, shuffle=True)
            val_ds = _make_indexed_dataset(val_index, shuffle=False)
            model = _build_keras_lstm(prepared.X_sequential.shape[1:])
            model.fit(
                train_ds,
                validation_data=val_ds,
                epochs=config.LSTM_EPOCHS,
                verbose=2,
            )
            y_score = model.predict(val_ds, verbose=0).ravel()
            y_pred = (y_score >= 0.5).astype(int)
            y_true = y_val
            metrics = calculate_binary_metrics(y_true, y_pred, y_score)
            fold_metrics.append(metrics)

            if use_mlflow:
                for metric_name, metric_value in metrics.items():
                    mlflow.log_metric(f"fold_{fold_index}_{metric_name}", metric_value)

            for row_index, sample_index in enumerate(val_index):
                prediction_rows.append(
                    {
                        "model_type": "lstm",
                        "algorithm": "TensorFlow Keras LSTM",
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

    from pathlib import Path

    from src.training.cross_validation import _persist_results

    result_path, predictions_path = _persist_results(
        output_root=Path(output_root),
        model_type="lstm",
        algorithm="TensorFlow Keras LSTM",
        n_splits=resolved_n_splits,
        random_state=config.RANDOM_SEED,
        window_size=prepared.window_size,
        hyperparameters={
            "epochs": config.LSTM_EPOCHS,
            "batch_size": config.LSTM_BATCH_SIZE,
        },
        fold_metrics=fold_metrics,
        summary=summary,
        prediction_rows=prediction_rows,
        fallback_used=False,
    )
    return ExperimentResult(
        model_type="lstm",
        algorithm="TensorFlow Keras LSTM",
        n_splits=resolved_n_splits,
        random_state=config.RANDOM_SEED,
        window_size=prepared.window_size,
        fold_metrics=fold_metrics,
        summary=summary,
        result_path=result_path,
        predictions_path=predictions_path,
        fallback_used=False,
    )


def _build_keras_lstm(input_shape: tuple[int, ...]):
    import tensorflow as tf

    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=input_shape),
            tf.keras.layers.LSTM(64),
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="cic", choices=["cic", "unsw"])
    parser.add_argument("--no-mlflow", action="store_true")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--no-mlp-fallback", action="store_true")
    args = parser.parse_args()

    prepared = prepare_windowed_binary_dataset(dataset=args.dataset)
    result = train_lstm_or_mlp(
        prepared=prepared,
        use_mlflow=not args.no_mlflow,
        output_dir=args.output_dir,
        allow_mlp_fallback=not args.no_mlp_fallback,
    )
    _print_summary(result)


def _print_summary(result: ExperimentResult) -> None:
    print(f"{result.algorithm} k-fold concluido")
    if result.fallback_used:
        print(f"Fallback documentado: {FALLBACK_REASON}")
    for metric_name in METRIC_NAMES:
        print(f"{metric_name}: {format_mean_std(result.summary[metric_name])}")


def _parse_hidden_layers(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


class _null_run:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_args: object) -> None:
        return None


if __name__ == "__main__":
    main()
