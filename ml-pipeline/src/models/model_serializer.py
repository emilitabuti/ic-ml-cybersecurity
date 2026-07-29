"""Serialização portável do modelo vencedor com pipeline de inferência."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import tempfile
from typing import Any

import joblib
import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)

ARTIFACT_VERSION = "1.0"
SKLEARN_MODEL_TYPES = {"random_forest", "decision_tree"}
LSTM_MODEL_TYPE = "lstm"
SUPPORTED_MODEL_TYPES = SKLEARN_MODEL_TYPES | {LSTM_MODEL_TYPE}

_REQUIRED_COMMON_KEYS = {
    "artifact_version",
    "model_type",
    "model_format",
    "scaler",
    "window_size",
    "window_transformer",
    "feature_names",
    "label_encoding",
}

DEFAULT_LABEL_ENCODING = {
    "target_column": "Binary_Label",
    "negative_class": {"id": 0, "label": "BENIGN"},
    "positive_class": {"id": 1, "label": "Attack"},
    "id_to_label": {0: "BENIGN", 1: "Attack"},
}


class ModelSerializationError(RuntimeError):
    """Erro de serialização ou inferência do artefato portável."""


def select_winning_model(comparison_csv: str | Path) -> str:
    """Seleciona o vencedor a partir do CSV comparativo real da Story 3.5.

    O vencedor é o modelo com mais métricas marcadas em ``best_metrics``. Em caso
    de empate, usa a maior média de F1 como critério secundário.
    """
    path = Path(comparison_csv)
    if not path.exists():
        raise FileNotFoundError(
            f"CSV comparativo não encontrado: {path}. Gere primeiro com "
            "python -m src.training.evaluator --results-dir <reports_dir> ..."
        )

    table = pd.read_csv(path)
    required_columns = {"model_type", "f1", "best_metrics"}
    missing_columns = required_columns.difference(table.columns)
    if missing_columns:
        raise ModelSerializationError(
            "CSV comparativo inválido; colunas ausentes: "
            f"{', '.join(sorted(missing_columns))}."
        )

    ranked = table.copy()
    ranked["best_metric_count"] = ranked["best_metrics"].fillna("").map(
        lambda value: len([item for item in str(value).split(",") if item.strip()])
    )
    ranked["f1_mean"] = ranked["f1"].map(_parse_metric_mean)
    winner = ranked.sort_values(
        ["best_metric_count", "f1_mean"],
        ascending=[False, False],
    ).iloc[0]
    model_type = str(winner["model_type"])
    if model_type not in SUPPORTED_MODEL_TYPES:
        raise ModelSerializationError(f"Modelo vencedor não suportado: {model_type}.")
    logger.info("Modelo vencedor selecionado pelo CSV %s: %s", path, model_type)
    return model_type


def serialize_model(
    *,
    model_path: str | Path,
    scaler_path: str | Path,
    output_path: str | Path,
    model_type: str,
    feature_names: list[str],
    window_size: int | None = None,
    label_encoding: dict[str, Any] | None = None,
    preprocessing: dict[str, Any] | None = None,
) -> Path:
    """Serializa modelo, scaler, janela e encoder binário em um único artefato.

    O artefato é um ``dict`` joblib com tipos portáveis, evitando dependência de
    classes deste módulo no momento de ``joblib.load`` em ambiente limpo.
    """
    resolved_model_type = _normalize_model_type(model_type)
    resolved_window_size = int(window_size or config.WINDOW_SIZE)
    _validate_window_size(resolved_window_size)
    resolved_feature_names = _validate_feature_names(feature_names)

    model = _load_model(model_path, resolved_model_type)
    keras_model_suffix = Path(model_path).suffix.lower() if resolved_model_type == LSTM_MODEL_TYPE else None
    scaler = _load_required_joblib(scaler_path, component_name="scaler")
    flatten = resolved_model_type in SKLEARN_MODEL_TYPES
    artifact = {
        "artifact_version": ARTIFACT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_type": resolved_model_type,
        "model_format": (
            f"keras_{keras_model_suffix.lstrip('.')}"
            if resolved_model_type == LSTM_MODEL_TYPE
            else "sklearn_joblib"
        ),
        "model": model if resolved_model_type in SKLEARN_MODEL_TYPES else None,
        "keras_model_bytes": model if resolved_model_type == LSTM_MODEL_TYPE else None,
        "keras_model_suffix": keras_model_suffix,
        "scaler": scaler,
        "window_size": resolved_window_size,
        "window_transformer": {
            "name": "sliding_window",
            "flatten": flatten,
            "label_strategy": "last_record",
        },
        "feature_names": resolved_feature_names,
        "label_encoding": label_encoding or DEFAULT_LABEL_ENCODING,
        "preprocessing": preprocessing or {},
        "random_seed": config.RANDOM_SEED,
    }
    validate_artifact(artifact)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output)
    logger.info("Artefato serializado salvo em: %s", output)
    return output


def serialize_winning_model(
    *,
    comparison_csv: str | Path,
    model_path: str | Path,
    scaler_path: str | Path,
    output_dir: str | Path | None = None,
    feature_names: list[str] | None = None,
    dataset: str = "cic",
    window_size: int | None = None,
) -> Path:
    """Seleciona o vencedor pelo CSV e serializa o pipeline completo."""
    model_type = select_winning_model(comparison_csv)
    names = feature_names or _load_feature_names(dataset)
    scaler = _load_required_joblib(scaler_path, component_name="scaler")
    preprocessing = _build_preprocessing_metadata(
        dataset=dataset,
        scaler=scaler,
        feature_names=names,
    )
    output_root = Path(output_dir or config.MODEL_PATH)
    extension = ".pkl"
    output_path = output_root / f"model_{_artifact_model_suffix(model_type)}{extension}"
    return serialize_model(
        model_path=model_path,
        scaler_path=scaler_path,
        output_path=output_path,
        model_type=model_type,
        feature_names=names,
        window_size=window_size,
        preprocessing=preprocessing,
    )


def load_serialized_model(path: str | Path) -> dict[str, Any]:
    """Carrega e valida um artefato serializado."""
    artifact = joblib.load(path)
    validate_artifact(artifact)
    logger.info("Artefato carregado e validado: %s", path)
    return artifact


def validate_artifact(artifact: Any) -> None:
    """Valida componentes obrigatórios para inferência."""
    if not isinstance(artifact, dict):
        raise ModelSerializationError(
            "Artefato inválido: esperado dict com modelo e pipeline de inferência."
        )

    missing = [
        key for key in sorted(_REQUIRED_COMMON_KEYS)
        if key not in artifact or artifact[key] is None
    ]
    if missing:
        raise ModelSerializationError(
            "Artefato inválido: componente(s) obrigatório(s) ausente(s): "
            f"{', '.join(missing)}."
        )

    model_type = _normalize_model_type(str(artifact["model_type"]))
    if model_type in SKLEARN_MODEL_TYPES and artifact.get("model") is None:
        raise ModelSerializationError(
            "Artefato inválido: componente obrigatório ausente: model."
        )
    if model_type == LSTM_MODEL_TYPE and not artifact.get("keras_model_bytes"):
        raise ModelSerializationError(
            "Artefato inválido: componente obrigatório ausente: keras_model_bytes."
        )

    window_transformer = artifact["window_transformer"]
    if (
        not isinstance(window_transformer, dict)
        or window_transformer.get("name") != "sliding_window"
    ):
        raise ModelSerializationError(
            "Artefato inválido: window_transformer deve descrever sliding_window."
        )

    _validate_window_size(int(artifact["window_size"]))
    _validate_feature_names(list(artifact["feature_names"]))
    _validate_label_encoding(artifact["label_encoding"])


def predict_from_artifact(
    artifact_or_path: dict[str, Any] | str | Path,
    X: pd.DataFrame | np.ndarray,
) -> dict[str, np.ndarray]:
    """Executa inferência usando somente componentes embutidos no artefato."""
    artifact = (
        load_serialized_model(artifact_or_path)
        if isinstance(artifact_or_path, (str, Path))
        else artifact_or_path
    )
    validate_artifact(artifact)

    X_array = _prepare_inference_features(X, artifact)
    windows = _create_inference_windows(
        X_array,
        window_size=int(artifact["window_size"]),
        flatten=bool(artifact["window_transformer"]["flatten"]),
    )

    model_type = _normalize_model_type(str(artifact["model_type"]))
    if model_type in SKLEARN_MODEL_TYPES:
        model = artifact["model"]
        predictions = np.asarray(model.predict(windows), dtype=int)
        confidences = _predict_sklearn_confidence(model, windows, predictions)
    else:
        keras_model = _load_keras_model_from_bytes(
            artifact["keras_model_bytes"],
            suffix=artifact.get("keras_model_suffix") or ".h5",
        )
        scores = np.asarray(keras_model.predict(windows, verbose=0)).reshape(-1)
        predictions = (scores >= 0.5).astype(int)
        confidences = np.where(predictions == 1, scores, 1.0 - scores)

    labels = _decode_labels(predictions, artifact["label_encoding"])
    return {
        "predictions": predictions,
        "labels": labels,
        "confidence": np.asarray(confidences, dtype=float),
    }


def default_scaler_path(dataset: str) -> Path:
    """Retorna o caminho padrão do scaler persistido pelo pipeline de dados."""
    if dataset == "cic":
        return Path("data/processed/cic_ids2017_scaled.joblib")
    if dataset == "unsw":
        return Path("data/processed/unsw_nb15_scaled.joblib")
    raise ValueError("dataset deve ser 'cic' ou 'unsw'.")


def default_cleaned_dataset_path(dataset: str) -> Path:
    """Retorna o parquet limpo usado para inferir metadata do preprocessing."""
    if dataset == "cic":
        return Path("data/processed/cic_ids2017_cleaned.parquet")
    if dataset == "unsw":
        return Path("data/processed/unsw_nb15_cleaned.parquet")
    raise ValueError("dataset deve ser 'cic' ou 'unsw'.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison-csv", required=True)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--scaler-path", default=None)
    parser.add_argument("--output-dir", default=config.MODEL_PATH)
    parser.add_argument("--dataset", choices=["cic", "unsw"], default="cic")
    parser.add_argument("--window-size", type=int, default=config.WINDOW_SIZE)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    scaler_path = args.scaler_path or default_scaler_path(args.dataset)
    serialize_winning_model(
        comparison_csv=args.comparison_csv,
        model_path=args.model_path,
        scaler_path=scaler_path,
        output_dir=args.output_dir,
        dataset=args.dataset,
        window_size=args.window_size,
    )


def _load_model(model_path: str | Path, model_type: str) -> Any:
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Modelo treinado não encontrado: {path}.")
    if model_type == LSTM_MODEL_TYPE:
        if path.suffix.lower() not in {".h5", ".keras"}:
            raise ModelSerializationError(
                "Modelo LSTM deve ser informado como arquivo .h5 ou .keras."
            )
        return path.read_bytes()
    return _load_required_joblib(path, component_name="model")


def _load_required_joblib(path: str | Path, *, component_name: str) -> Any:
    resolved_path = Path(path)
    if not resolved_path.exists():
        raise FileNotFoundError(
            f"Componente obrigatório não encontrado ({component_name}): {resolved_path}."
        )
    component = joblib.load(resolved_path)
    if component is None:
        raise ModelSerializationError(
            f"Componente obrigatório vazio ao carregar {component_name}: {resolved_path}."
        )
    return component


def _load_feature_names(dataset: str) -> list[str]:
    from src.data.data_loader import get_feature_names

    return get_feature_names(dataset=dataset, task="binary")


def _build_preprocessing_metadata(
    *,
    dataset: str,
    scaler: Any,
    feature_names: list[str],
) -> dict[str, Any]:
    scaler_feature_names = [
        str(name) for name in getattr(scaler, "feature_names_in_", [])
    ]
    cleaned_path = default_cleaned_dataset_path(dataset)
    log1p_feature_names: list[str] = []
    if cleaned_path.exists() and scaler_feature_names:
        cleaned = pd.read_parquet(cleaned_path, columns=scaler_feature_names)
        log1p_feature_names = [
            column
            for column in scaler_feature_names
            if cleaned[column].min() >= 0 and cleaned[column].max() > 1e6
        ]

    categorical_feature_names = [
        column
        for column in ["proto", "state", "service"]
        if any(name.startswith(f"{column}_") for name in feature_names)
    ]
    return {
        "dataset": dataset,
        "scaler_feature_names": scaler_feature_names,
        "log1p_feature_names": log1p_feature_names,
        "categorical_feature_names": categorical_feature_names,
        "model_ready_feature_names": list(feature_names),
    }


def _create_inference_windows(
    X: np.ndarray,
    *,
    window_size: int,
    flatten: bool,
) -> np.ndarray:
    if X.shape[0] < window_size:
        raise ModelSerializationError(
            "Entrada insuficiente para sliding window: "
            f"{X.shape[0]} amostras recebidas, window_size={window_size}."
        )
    n_windows = X.shape[0] - window_size + 1
    windows = np.stack([X[start : start + window_size] for start in range(n_windows)])
    if flatten:
        return windows.reshape(n_windows, -1)
    return windows


def _prepare_inference_features(
    X: pd.DataFrame | np.ndarray,
    artifact: dict[str, Any],
) -> np.ndarray:
    if isinstance(X, pd.DataFrame):
        return _prepare_dataframe_features(X, artifact)

    X_array = np.asarray(X, dtype=np.float32)
    _validate_inference_input(X_array, artifact)
    return _prepare_array_features(X_array, artifact)


def _prepare_dataframe_features(
    df: pd.DataFrame,
    artifact: dict[str, Any],
) -> np.ndarray:
    preprocessing = artifact.get("preprocessing") or {}
    feature_names = list(artifact["feature_names"])
    categorical_names = preprocessing.get("categorical_feature_names") or []
    scaler_feature_names = preprocessing.get("scaler_feature_names") or list(
        getattr(artifact["scaler"], "feature_names_in_", [])
    )

    if categorical_names and all(column in df.columns for column in categorical_names):
        prepared = df.copy()
        _scale_dataframe_numeric_features(prepared, artifact)
        prepared = pd.get_dummies(
            prepared,
            columns=[column for column in categorical_names if column in prepared.columns],
            drop_first=False,
        )
        prepared = prepared.reindex(columns=feature_names, fill_value=0)
        return (
            prepared.apply(pd.to_numeric, errors="coerce")
            .fillna(0)
            .to_numpy(dtype=np.float32)
        )

    if all(column in df.columns for column in feature_names):
        prepared = df[feature_names].apply(pd.to_numeric, errors="coerce").fillna(0)
        if scaler_feature_names and len(scaler_feature_names) == len(feature_names):
            prepared = pd.DataFrame(
                artifact["scaler"].transform(prepared),
                columns=feature_names,
                index=prepared.index,
            )
        return prepared.to_numpy(dtype=np.float32)

    missing = [column for column in feature_names if column not in df.columns]
    raise ModelSerializationError(
        "DataFrame de inferência não contém as features esperadas pelo artefato. "
        f"Primeiras colunas ausentes: {missing[:10]}."
    )


def _scale_dataframe_numeric_features(
    df: pd.DataFrame,
    artifact: dict[str, Any],
) -> None:
    preprocessing = artifact.get("preprocessing") or {}
    scaler_feature_names = preprocessing.get("scaler_feature_names") or list(
        getattr(artifact["scaler"], "feature_names_in_", [])
    )
    missing_numeric = [
        column for column in scaler_feature_names if column not in df.columns
    ]
    if missing_numeric:
        raise ModelSerializationError(
            "DataFrame de inferência não contém colunas numéricas exigidas pelo "
            f"scaler. Primeiras ausentes: {missing_numeric[:10]}."
        )

    numeric = df[scaler_feature_names].apply(pd.to_numeric, errors="coerce")
    for column in preprocessing.get("log1p_feature_names") or []:
        numeric[column] = np.log1p(numeric[column].clip(lower=0))
    numeric = numeric.replace([np.inf, -np.inf], np.nan).fillna(0)
    df[scaler_feature_names] = artifact["scaler"].transform(numeric)


def _prepare_array_features(X: np.ndarray, artifact: dict[str, Any]) -> np.ndarray:
    expected_features = len(artifact["feature_names"])
    scaler_feature_count = int(
        getattr(artifact["scaler"], "n_features_in_", expected_features)
    )
    if X.shape[1] == expected_features:
        if scaler_feature_count == expected_features:
            return np.asarray(artifact["scaler"].transform(X), dtype=np.float32)
        return X
    if X.shape[1] == scaler_feature_count:
        return np.asarray(artifact["scaler"].transform(X), dtype=np.float32)
    raise ModelSerializationError(
        "Quantidade de features incompatível com o artefato: "
        f"recebidas={X.shape[1]}, esperadas={expected_features} "
        f"ou {scaler_feature_count} para entrada pré-one-hot."
    )


def _predict_sklearn_confidence(
    model: Any,
    X: np.ndarray,
    predictions: np.ndarray,
) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        probabilities = np.asarray(model.predict_proba(X), dtype=float)
        if probabilities.ndim == 2:
            classes = list(getattr(model, "classes_", []))
            if classes:
                return np.asarray(
                    [
                        probabilities[row_index, classes.index(prediction)]
                        for row_index, prediction in enumerate(predictions)
                    ],
                    dtype=float,
                )
            return probabilities.max(axis=1)
        return probabilities
    if hasattr(model, "decision_function"):
        scores = np.asarray(model.decision_function(X), dtype=float)
        return 1.0 / (1.0 + np.exp(-scores))
    return np.ones(predictions.shape[0], dtype=float)


def _load_keras_model_from_bytes(model_bytes: bytes, *, suffix: str = ".h5") -> Any:
    try:
        import tensorflow as tf
    except ModuleNotFoundError as exc:
        raise ModelSerializationError(
            "TensorFlow é necessário para inferência com artefato LSTM (.h5)."
        ) from exc

    with tempfile.NamedTemporaryFile(suffix=suffix) as temporary_model:
        temporary_model.write(model_bytes)
        temporary_model.flush()
        return tf.keras.models.load_model(temporary_model.name)


def _decode_labels(predictions: np.ndarray, label_encoding: dict[str, Any]) -> np.ndarray:
    id_to_label = {
        int(class_id): label
        for class_id, label in label_encoding["id_to_label"].items()
    }
    return np.asarray(
        [id_to_label.get(int(prediction), str(prediction)) for prediction in predictions],
        dtype=object,
    )


def _validate_inference_input(X: np.ndarray, artifact: dict[str, Any]) -> None:
    if X.ndim != 2:
        raise ModelSerializationError(
            "Entrada de inferência deve ser 2D: shape (n_samples, n_features)."
        )
    expected_features = len(artifact["feature_names"])
    scaler_feature_count = int(
        getattr(artifact["scaler"], "n_features_in_", expected_features)
    )
    if X.shape[1] not in {expected_features, scaler_feature_count}:
        raise ModelSerializationError(
            "Quantidade de features incompatível com o artefato: "
            f"recebidas={X.shape[1]}, esperadas={expected_features} "
            f"ou {scaler_feature_count} para entrada pré-one-hot."
        )


def _validate_feature_names(feature_names: list[str]) -> list[str]:
    if not feature_names or not all(
        isinstance(name, str) and name for name in feature_names
    ):
        raise ModelSerializationError("feature_names deve conter nomes de features não vazios.")
    return list(feature_names)


def _validate_label_encoding(label_encoding: Any) -> None:
    if not isinstance(label_encoding, dict) or "id_to_label" not in label_encoding:
        raise ModelSerializationError(
            "label_encoding deve conter o mapeamento obrigatório id_to_label."
        )
    ids = {int(key) for key in label_encoding["id_to_label"].keys()}
    if ids != {0, 1}:
        raise ModelSerializationError(
            "label_encoding inválido: id_to_label deve mapear as classes 0 e 1."
        )


def _validate_window_size(window_size: int) -> None:
    if window_size not in {5, 10, 20}:
        raise ModelSerializationError(
            "window_size deve ser um dos valores permitidos: 5, 10 ou 20. "
            f"Recebido: {window_size}."
        )


def _normalize_model_type(model_type: str) -> str:
    normalized = model_type.strip().lower()
    aliases = {"rf": "random_forest", "dt": "decision_tree"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_MODEL_TYPES:
        raise ModelSerializationError(
            "model_type inválido. Use random_forest, decision_tree ou lstm."
        )
    return normalized


def _artifact_model_suffix(model_type: str) -> str:
    if model_type == "random_forest":
        return "rf"
    if model_type == "decision_tree":
        return "dt"
    return "lstm"


def _parse_metric_mean(value: Any) -> float:
    return float(str(value).split("+/-", maxsplit=1)[0].strip())


if __name__ == "__main__":
    main()
