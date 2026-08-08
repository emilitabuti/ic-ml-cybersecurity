"""Ajuste final e avaliação temporal única conforme ``protocol.json``.

A execução possui duas fases. A primeira ajusta pré-processador, ranking e os
três modelos somente em treino+validação. A segunda cria um marcador durável
antes do primeiro acesso ao teste, transforma o teste uma vez sem refit e
avalia todas as configurações congeladas na mesma execução.
"""

from __future__ import annotations

import argparse
import gc
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from time import perf_counter
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
from sklearn.tree import DecisionTreeClassifier

from src.features.feature_selector import RandomForestFeatureSelector
from src.features.fold_preprocessor import (
    CATEGORICAL_CANDIDATES,
    NON_FEATURE_COLUMNS,
    FoldPreprocessor,
)
from src.features.partition_window_builder import iter_partition_window_batches
from src.training.metrics import calculate_binary_metrics


DEFAULT_RAW_DIR = Path("data/processed/unsw_nb15_temporal")
DEFAULT_CACHE_DIR = Path("data/processed/unsw_nb15_temporal_final")
DEFAULT_REPORT_DIR = Path("reports_temporal/unsw/final_evaluation")
DEFAULT_PROTOCOL_PATH = Path("reports_temporal/unsw/protocol.json")
FINAL_SUMMARY_PATH = Path("reports_temporal/unsw/final_test_metrics.json")
METADATA_COLUMNS = (
    "record_id",
    "temporal_session",
    "split",
    "Binary_Label",
    "attack_cat",
    "source_file",
    "Stime",
    "Ltime",
)


def prepare_final_models(
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    protocol_path: str | Path = DEFAULT_PROTOCOL_PATH,
) -> dict[str, Any]:
    """Ajusta todo o estado final sem carregar o teste."""
    raw_root = Path(raw_dir)
    cache_root = Path(cache_dir)
    report_root = Path(report_dir)
    protocol_file = Path(protocol_path)
    protocol, protocol_sha = _load_and_validate_protocol(protocol_file)
    state_path = report_root / "run_state.json"
    if FINAL_SUMMARY_PATH.exists():
        raise FileExistsError("A avaliação final já foi concluída e não pode ser repetida.")
    if state_path.exists():
        state = _load_json(state_path)
        if state["status"] in {"prepared", "test_opened", "test_transformed", "completed"}:
            return state
        raise RuntimeError(f"Estado final inesperado: {state['status']}")

    partition_protocol = protocol["temporal_protocol"]["partitions"]
    train_path = raw_root / "train.parquet"
    validation_path = raw_root / "validation.parquet"
    _verify_file_sha256(train_path, partition_protocol["train"]["sha256"])
    _verify_file_sha256(validation_path, partition_protocol["validation"]["sha256"])

    print("[final] carregando treino+validação; teste permanece fechado", flush=True)
    train = pd.read_parquet(train_path)
    validation = pd.read_parquet(validation_path)
    development = pd.concat([train, validation], ignore_index=True)
    del train, validation
    if len(development) != protocol["final_fit"]["fit_rows_before_windowing"]:
        raise RuntimeError("Quantidade de linhas de desenvolvimento diverge do protocolo.")
    if not development["record_id"].is_unique:
        raise RuntimeError("record_id duplicado em treino+validação.")
    development["split"] = "train"
    development = _ensure_writable_numeric_conversion(development)

    report_root.mkdir(parents=True, exist_ok=False)
    cache_root.mkdir(parents=True, exist_ok=False)
    preprocessor_path = report_root / "preprocessor_train_validation.joblib"
    selector_path = report_root / "feature_ranking_train_validation.json"

    print("[final] ajustando pré-processador em treino+validação", flush=True)
    preprocessor = FoldPreprocessor().fit(development)
    preprocessor.save(preprocessor_path)
    preprocessor_state = _logical_preprocessor_sha256(preprocessor)
    transformed = preprocessor.transform(development)

    selector_config = protocol["final_fit"]["selector"]
    print("[final] ajustando ranking top_30 em treino+validação", flush=True)
    selector = RandomForestFeatureSelector(
        feature_names=transformed.columns.tolist(),
        top_n=int(selector_config["fit_once_to_top_n"]),
        threshold=0.0,
        artifact_path=selector_path,
        random_state=int(selector_config["random_state"]),
        n_estimators=int(selector_config["n_estimators"]),
        n_jobs=int(selector_config["n_jobs"]),
    ).fit(
        transformed.to_numpy(dtype=np.float32, copy=False),
        development["Binary_Label"].to_numpy(dtype=np.int8),
        partition="train",
        record_ids=development["record_id"].to_numpy(dtype=np.int64),
    )
    selector.save()
    selected_names = list(selector.selected_feature_names_)
    selected = pd.concat(
        [
            development[list(METADATA_COLUMNS)].reset_index(drop=True),
            transformed[selected_names].reset_index(drop=True),
        ],
        axis=1,
    )
    train_cache = cache_root / "train_validation_top_30.parquet"
    _atomic_write_parquet(selected, train_cache)
    del development, transformed, preprocessor, selector
    gc.collect()

    training: dict[str, Any] = {}
    configurations = protocol["selected_configuration_by_algorithm"]
    for algorithm in ("decision_tree", "random_forest", "lstm"):
        configuration = configurations[algorithm]
        top_n = int(configuration["top_n"])
        feature_names = selected_names[:top_n]
        print(f"[final] treinando {algorithm} com top_{top_n}", flush=True)
        model_path = report_root / "models" / _model_filename(algorithm)
        started = perf_counter()
        model = _fit_model(
            algorithm,
            configuration["hyperparameters"],
            selected,
            feature_names,
            window_size=int(protocol["final_fit"]["window_size"]),
            tree_batch_size=int(
                protocol["final_fit"]["window_materialization_batch_size_tree_models"]
            ),
        )
        fit_seconds = perf_counter() - started
        _save_model(model, algorithm, model_path)
        training[algorithm] = {
            "variant": configuration["variant"],
            "feature_count": top_n,
            "feature_names": feature_names,
            "feature_names_sha256": _names_sha256(feature_names),
            "fit_seconds": fit_seconds,
            "model_path": str(model_path),
            "model_sha256": _file_sha256(model_path),
            "artifact_size_bytes": model_path.stat().st_size,
        }
        _clear_model(model, algorithm)
        del model
        gc.collect()

    preparation = {
        "status": "prepared",
        "protocol_sha256": protocol_sha,
        "fit_partitions": ["train", "validation"],
        "fit_rows": int(len(selected)),
        "fit_record_ids_sha256": _record_ids_sha256(
            selected["record_id"].to_numpy(dtype=np.int64)
        ),
        "preprocessor_path": str(preprocessor_path),
        "preprocessor_sha256": _file_sha256(preprocessor_path),
        "preprocessor_logical_state_sha256": preprocessor_state,
        "selector_path": str(selector_path),
        "selector_sha256": _file_sha256(selector_path),
        "selected_top_30_names": selected_names,
        "selected_top_30_names_sha256": _names_sha256(selected_names),
        "train_cache_path": str(train_cache),
        "train_cache_sha256": _file_sha256(train_cache),
        "training": training,
        "test_accessed": False,
        "raw_test_reads": 0,
    }
    _atomic_write_json(preparation, report_root / "preparation_audit.json")
    _atomic_write_json(preparation, state_path)
    print("[final] três modelos preparados; teste ainda fechado", flush=True)
    return preparation


def evaluate_closed_test_once(
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    protocol_path: str | Path = DEFAULT_PROTOCOL_PATH,
) -> dict[str, Any]:
    """Abre o teste uma vez e avalia as três configurações já congeladas."""
    raw_root = Path(raw_dir)
    cache_root = Path(cache_dir)
    report_root = Path(report_dir)
    protocol_file = Path(protocol_path)
    protocol, protocol_sha = _load_and_validate_protocol(protocol_file)
    state_path = report_root / "run_state.json"
    if FINAL_SUMMARY_PATH.exists():
        raise FileExistsError("A avaliação final já foi concluída e não pode ser repetida.")
    if not state_path.exists():
        raise RuntimeError("Os modelos finais precisam ser preparados antes de abrir o teste.")
    state = _load_json(state_path)
    if state["protocol_sha256"] != protocol_sha:
        raise RuntimeError("O protocolo mudou depois da preparação dos modelos.")
    _verify_prepared_artifacts(state)

    test_cache = cache_root / "test_top_30.parquet"
    if not test_cache.exists():
        if state["status"] != "prepared":
            raise RuntimeError("Marcador indica teste aberto, mas o cache não existe.")
        state.update(
            {
                "status": "test_opened",
                "test_accessed": True,
                "raw_test_reads": 1,
            }
        )
        _atomic_write_json(state, state_path)
        print("[final] TESTE ABERTO: primeira e única leitura bruta", flush=True)
        test_path = raw_root / "test.parquet"
        expected_test = protocol["temporal_protocol"]["partitions"]["test"]
        _verify_file_sha256(test_path, expected_test["sha256"])
        test = pd.read_parquet(test_path)
        if len(test) != expected_test["rows"]:
            raise RuntimeError("Quantidade de linhas do teste diverge do protocolo.")
        test = _ensure_writable_numeric_conversion(test)
        preprocessor = FoldPreprocessor.load(state["preprocessor_path"])
        selector = RandomForestFeatureSelector.load(state["selector_path"])
        before = _logical_preprocessor_sha256(preprocessor)
        transformed = preprocessor.transform(test)
        selected_names = state["selected_top_30_names"]
        selected = pd.concat(
            [
                test[list(METADATA_COLUMNS)].reset_index(drop=True),
                transformed[selected_names].reset_index(drop=True),
            ],
            axis=1,
        )
        if _logical_preprocessor_sha256(preprocessor) != before:
            raise RuntimeError("A transformação do teste alterou o pré-processador.")
        if selector.selected_feature_names_ != selected_names:
            raise RuntimeError("O ranking carregado diverge do ranking preparado.")
        _atomic_write_parquet(selected, test_cache)
        state.update(
            {
                "status": "test_transformed",
                "test_cache_path": str(test_cache),
                "test_cache_sha256": _file_sha256(test_cache),
                "test_rows": int(len(selected)),
                "preprocessor_unchanged_by_test": True,
                "selector_unchanged_by_test": True,
            }
        )
        _atomic_write_json(state, state_path)
        del test, transformed, selected, preprocessor, selector
        gc.collect()
    else:
        if state["raw_test_reads"] != 1 or not state["test_accessed"]:
            raise RuntimeError("Cache de teste sem marcador válido de abertura única.")
        _verify_file_sha256(test_cache, state["test_cache_sha256"])

    test_selected = pd.read_parquet(test_cache)
    results: dict[str, Any] = {}
    for algorithm in ("decision_tree", "random_forest", "lstm"):
        result_path = report_root / "metrics" / f"{algorithm}.json"
        if result_path.exists():
            result = _load_json(result_path)
        else:
            training = state["training"][algorithm]
            print(f"[final] avaliando {algorithm} no teste fechado", flush=True)
            model = _load_model(Path(training["model_path"]), algorithm)
            started = perf_counter()
            predictions = _predict_batches(
                model,
                algorithm,
                test_selected,
                training["feature_names"],
                window_size=int(protocol["final_fit"]["window_size"]),
                batch_size=(
                    int(protocol["selected_configuration_by_algorithm"]["lstm"]["hyperparameters"]["batch_size"])
                    if algorithm == "lstm"
                    else int(protocol["final_fit"]["window_materialization_batch_size_tree_models"])
                ),
                threshold=float(protocol["task"]["classification_threshold"]),
            )
            inference_seconds = perf_counter() - started
            predictions_path = report_root / "predictions" / f"{algorithm}.parquet"
            _atomic_write_parquet(predictions, predictions_path)
            result = _build_test_result(
                algorithm,
                training,
                predictions,
                predictions_path,
                inference_seconds=inference_seconds,
                protocol_sha256=protocol_sha,
            )
            _atomic_write_json(result, result_path)
            _clear_model(model, algorithm)
            del model, predictions
            gc.collect()
        results[algorithm] = result

    summary = {
        "schema_version": "1.0",
        "status": "completed_single_closed_test_evaluation",
        "protocol_path": str(protocol_file),
        "protocol_sha256": protocol_sha,
        "test_raw_reads": 1,
        "test_evaluation_runs": 1,
        "models_evaluated_together": [
            "decision_tree",
            "random_forest",
            "lstm",
        ],
        "selection_or_tuning_on_test": False,
        "results": results,
    }
    _atomic_write_json(summary, FINAL_SUMMARY_PATH)
    summary_sha = _file_sha256(FINAL_SUMMARY_PATH)
    _atomic_write_text(
        f"{summary_sha}  {FINAL_SUMMARY_PATH.name}\n",
        FINAL_SUMMARY_PATH.with_suffix(".json.sha256"),
    )
    state.update(
        {
            "status": "completed",
            "final_summary_path": str(FINAL_SUMMARY_PATH),
            "final_summary_sha256": summary_sha,
        }
    )
    _atomic_write_json(state, state_path)
    print("[final] avaliação temporal única concluída", flush=True)
    return summary


def _fit_model(
    algorithm: str,
    parameters: dict[str, Any],
    train: pd.DataFrame,
    feature_names: list[str],
    *,
    window_size: int,
    tree_batch_size: int,
) -> Any:
    if algorithm == "lstm":
        return _fit_lstm(train, feature_names, parameters, window_size=window_size)
    X, y = _collect_windows(
        train,
        feature_names,
        window_size=window_size,
        batch_size=tree_batch_size,
    )
    if algorithm == "decision_tree":
        model = DecisionTreeClassifier(
            max_depth=int(parameters["max_depth"]),
            random_state=int(parameters["random_state"]),
        )
    elif algorithm == "random_forest":
        model = RandomForestClassifier(
            n_estimators=int(parameters["n_estimators"]),
            max_depth=int(parameters["max_depth"]),
            n_jobs=int(parameters["n_jobs"]),
            random_state=int(parameters["random_state"]),
        )
    else:
        raise ValueError(f"Algoritmo desconhecido: {algorithm}")
    model.fit(X, y)
    del X, y
    gc.collect()
    return model


def _fit_lstm(
    train: pd.DataFrame,
    feature_names: list[str],
    parameters: dict[str, Any],
    *,
    window_size: int,
) -> Any:
    import tensorflow as tf

    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(int(parameters["random_state"]))
    try:
        tf.config.experimental.enable_op_determinism()
    except (AttributeError, RuntimeError):
        pass
    batch_size = int(parameters["batch_size"])

    def generator():
        for batch in iter_partition_window_batches(
            train,
            feature_names,
            window_size=window_size,
            batch_size=batch_size,
            expected_split="train",
        ):
            yield batch.X, batch.y.astype(np.float32)

    dataset = tf.data.Dataset.from_generator(
        generator,
        output_signature=(
            tf.TensorSpec((None, window_size, len(feature_names)), tf.float32),
            tf.TensorSpec((None,), tf.float32),
        ),
    ).repeat().prefetch(1)
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input((window_size, len(feature_names))),
            tf.keras.layers.LSTM(64),
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(optimizer=parameters["optimizer"], loss=parameters["loss"])
    model.fit(
        dataset,
        epochs=int(parameters["epochs"]),
        steps_per_epoch=_window_batch_count(train, window_size, batch_size),
        shuffle=False,
        verbose=2,
    )
    return model


def _collect_windows(
    frame: pd.DataFrame,
    feature_names: list[str],
    *,
    window_size: int,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    X_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    for batch in iter_partition_window_batches(
        frame,
        feature_names,
        window_size=window_size,
        batch_size=batch_size,
        expected_split="train",
    ):
        X_parts.append(batch.flatten())
        y_parts.append(batch.y.astype(np.int8, copy=False))
    return np.concatenate(X_parts), np.concatenate(y_parts)


def _predict_batches(
    model: Any,
    algorithm: str,
    frame: pd.DataFrame,
    feature_names: list[str],
    *,
    window_size: int,
    batch_size: int,
    threshold: float,
) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for batch in iter_partition_window_batches(
        frame,
        feature_names,
        window_size=window_size,
        batch_size=batch_size,
        expected_split="test",
    ):
        values = batch.X if algorithm == "lstm" else batch.flatten()
        score = (
            np.asarray(model.predict_on_batch(values)).reshape(-1)
            if algorithm == "lstm"
            else np.asarray(model.predict_proba(values))[:, 1]
        )
        parts.append(
            pd.DataFrame(
                {
                    "target_record_id": batch.target_record_ids,
                    "temporal_session": batch.temporal_sessions,
                    "source_file": batch.source_files,
                    "attack_type": batch.attack_types,
                    "y_true": batch.y.astype(np.int8, copy=False),
                    "y_pred": (score >= threshold).astype(np.int8),
                    "y_score": score.astype(np.float64, copy=False),
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def _build_test_result(
    algorithm: str,
    training: dict[str, Any],
    predictions: pd.DataFrame,
    predictions_path: Path,
    *,
    inference_seconds: float,
    protocol_sha256: str,
) -> dict[str, Any]:
    y_true = predictions["y_true"].to_numpy(dtype=np.int8)
    y_pred = predictions["y_pred"].to_numpy(dtype=np.int8)
    y_score = predictions["y_score"].to_numpy(dtype=np.float64)
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    sessions: dict[str, Any] = {}
    for session, frame in predictions.groupby("temporal_session", sort=True):
        sessions[str(int(session))] = calculate_binary_metrics(
            frame["y_true"], frame["y_pred"], frame["y_score"]
        )
    attack_types: dict[str, Any] = {}
    malicious = sorted(
        predictions.loc[predictions["y_true"] == 1, "attack_type"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    for attack_type in malicious:
        subset = predictions[
            (predictions["y_true"] == 0)
            | (
                (predictions["y_true"] == 1)
                & (predictions["attack_type"].astype(str) == attack_type)
            )
        ]
        attack_types[attack_type] = {
            "positive_examples": int(
                ((subset["y_true"] == 1)).sum()
            ),
            "metrics": calculate_binary_metrics(
                subset["y_true"], subset["y_pred"], subset["y_score"]
            ),
        }
    return {
        "algorithm": algorithm,
        "variant": training["variant"],
        "protocol_sha256": protocol_sha256,
        "test_windows": int(len(predictions)),
        "feature_count": int(training["feature_count"]),
        "feature_names": training["feature_names"],
        "feature_names_sha256": training["feature_names_sha256"],
        "fit_seconds": float(training["fit_seconds"]),
        "inference_seconds": float(inference_seconds),
        "artifact_size_bytes": int(training["artifact_size_bytes"]),
        "metrics": calculate_binary_metrics(y_true, y_pred, y_score),
        "confusion_matrix": {
            "tn": int(matrix[0, 0]),
            "fp": int(matrix[0, 1]),
            "fn": int(matrix[1, 0]),
            "tp": int(matrix[1, 1]),
        },
        "metrics_by_session": sessions,
        "metrics_by_attack_type": attack_types,
        "predictions_path": str(predictions_path),
        "predictions_sha256": _file_sha256(predictions_path),
        "test_evaluation_run": 1,
        "selection_or_tuning_on_test": False,
    }


def _load_and_validate_protocol(path: Path) -> tuple[dict[str, Any], str]:
    protocol = _load_json(path)
    actual = _file_sha256(path)
    sidecar = path.with_suffix(".json.sha256").read_text(encoding="utf-8").split()[0]
    if actual != sidecar:
        raise RuntimeError("SHA-256 de protocol.json inválido.")
    if protocol["status"] != "frozen_before_closed_test":
        raise RuntimeError("O protocolo não está congelado antes do teste.")
    if protocol["test_policy"]["test_access_at_freeze"]:
        raise RuntimeError("O protocolo declara acesso prévio ao teste.")
    return protocol, actual


def _verify_prepared_artifacts(state: dict[str, Any]) -> None:
    for key in ("preprocessor", "selector"):
        _verify_file_sha256(Path(state[f"{key}_path"]), state[f"{key}_sha256"])
    for training in state["training"].values():
        _verify_file_sha256(Path(training["model_path"]), training["model_sha256"])


def _save_model(model: Any, algorithm: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if algorithm == "lstm":
        temporary = path.with_name(f".{path.stem}.tmp.keras")
        model.save(temporary, overwrite=True)
        temporary.replace(path)
    else:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
        try:
            joblib.dump(model, temporary)
            temporary.replace(path)
        finally:
            if temporary.exists():
                temporary.unlink()


def _load_model(path: Path, algorithm: str) -> Any:
    if algorithm == "lstm":
        import tensorflow as tf

        return tf.keras.models.load_model(path)
    return joblib.load(path)


def _clear_model(model: Any, algorithm: str) -> None:
    if algorithm == "lstm":
        import tensorflow as tf

        tf.keras.backend.clear_session()


def _model_filename(algorithm: str) -> str:
    return f"{algorithm}.keras" if algorithm == "lstm" else f"{algorithm}.joblib"


def _window_batch_count(frame: pd.DataFrame, window_size: int, batch_size: int) -> int:
    change = (
        frame["temporal_session"].ne(frame["temporal_session"].shift())
        | frame["source_file"].astype(str).ne(frame["source_file"].astype(str).shift())
    )
    counts = change.cumsum().value_counts(sort=False)
    return int(
        sum(
            (windows + batch_size - 1) // batch_size
            for count in counts
            if (windows := max(0, int(count) - window_size + 1))
        )
    )


def _logical_preprocessor_sha256(preprocessor: FoldPreprocessor) -> str:
    payload = json.dumps(
        preprocessor.audit_metadata(), sort_keys=True, separators=(",", ":")
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _ensure_writable_numeric_conversion(frame: pd.DataFrame) -> pd.DataFrame:
    if int(pd.__version__.split(".", maxsplit=1)[0]) < 3:
        return frame
    result = frame.copy()
    for column in result.columns:
        if (
            column not in NON_FEATURE_COLUMNS
            and column not in CATEGORICAL_CANDIDATES
            and pd.api.types.is_numeric_dtype(result[column].dtype)
        ):
            result[column] = result[column].astype("Float64")
    return result


def _names_sha256(names: Iterable[str]) -> str:
    return sha256("\n".join(names).encode("utf-8")).hexdigest()


def _record_ids_sha256(ids: np.ndarray) -> str:
    return sha256(np.asarray(ids, dtype="<i8").tobytes()).hexdigest()


def _verify_file_sha256(path: Path, expected: str) -> None:
    actual = _file_sha256(path)
    if actual != expected:
        raise RuntimeError(f"SHA-256 divergente para {path}: {actual} != {expected}")


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    try:
        json.loads(temporary.read_text(encoding="utf-8"))
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        frame.to_parquet(temporary, index=False)
        if len(pd.read_parquet(temporary, columns=[frame.columns[0]])) != len(frame):
            raise RuntimeError("Parquet temporário possui contagem divergente.")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_text(content: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--evaluate-only", action="store_true")
    args = parser.parse_args()
    if args.prepare_only and args.evaluate_only:
        parser.error("Escolha apenas uma fase.")
    if not args.evaluate_only:
        prepare_final_models()
    if not args.prepare_only:
        summary = evaluate_closed_test_once()
        print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
