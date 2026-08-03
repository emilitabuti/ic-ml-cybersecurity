"""Carregamento e inferência do artefato temporal canônico."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)

ARTIFACT_VERSION = "2.0"
PIPELINE_KIND = "temporal_raw_v2"
DEFAULT_LABEL_ENCODING = {
    "target_column": "Binary_Label",
    "negative_class": {"id": 0, "label": "BENIGN"},
    "positive_class": {"id": 1, "label": "Attack"},
    "id_to_label": {0: "BENIGN", 1: "Attack"},
}

_REQUIRED_KEYS = {
    "artifact_version",
    "pipeline_kind",
    "model_type",
    "model_format",
    "model",
    "preprocessor_state",
    "raw_feature_names",
    "raw_numeric_feature_names",
    "raw_categorical_feature_names",
    "selected_feature_names",
    "feature_names",
    "window_size",
    "window_transformer",
    "label_encoding",
    "classification_threshold",
    "protocol_sha256",
    "final_metrics_sha256",
}


class ModelSerializationError(RuntimeError):
    """Artefato ou entrada incompatível com o pipeline canônico."""


def load_serialized_model(path: str | Path) -> dict[str, Any]:
    """Carrega e valida o único formato de artefato suportado."""
    artifact = joblib.load(path)
    validate_artifact(artifact)
    logger.info("Artefato temporal carregado e validado: %s", path)
    return artifact


def validate_artifact(artifact: Any) -> None:
    """Valida o Random Forest temporal com pré-processamento embutido."""
    if not isinstance(artifact, dict):
        raise ModelSerializationError("Artefato inválido: esperado dicionário.")
    missing = [
        key for key in sorted(_REQUIRED_KEYS)
        if key not in artifact or artifact[key] is None
    ]
    if missing:
        raise ModelSerializationError(
            "Artefato inválido; componente(s) ausente(s): " + ", ".join(missing)
        )
    if artifact["artifact_version"] != ARTIFACT_VERSION:
        raise ModelSerializationError(
            f"Versão incompatível: {artifact['artifact_version']}; "
            f"esperada {ARTIFACT_VERSION}."
        )
    if artifact["pipeline_kind"] != PIPELINE_KIND:
        raise ModelSerializationError(
            f"Pipeline incompatível: {artifact['pipeline_kind']}; esperado {PIPELINE_KIND}."
        )
    if artifact["model_type"] != "random_forest":
        raise ModelSerializationError("O artefato canônico deve usar random_forest.")
    if not hasattr(artifact["model"], "predict_proba"):
        raise ModelSerializationError("O modelo deve implementar predict_proba().")
    if not isinstance(artifact["preprocessor_state"], dict):
        raise ModelSerializationError("preprocessor_state deve ser um dicionário.")

    raw_names = _feature_names(artifact["raw_feature_names"], "raw_feature_names")
    numeric = _feature_names(
        artifact["raw_numeric_feature_names"], "raw_numeric_feature_names"
    )
    categorical = _feature_names(
        artifact["raw_categorical_feature_names"], "raw_categorical_feature_names"
    )
    selected = _feature_names(
        artifact["selected_feature_names"], "selected_feature_names"
    )
    if set(numeric).intersection(categorical):
        raise ModelSerializationError("Features numéricas e categóricas se sobrepõem.")
    if set(raw_names) != set(numeric) | set(categorical):
        raise ModelSerializationError("O esquema bruto diverge do esquema tipado.")
    if selected != list(artifact["feature_names"]):
        raise ModelSerializationError("feature_names deve coincidir com top_30.")
    if len(selected) != 30:
        raise ModelSerializationError("O artefato deve conter exatamente 30 atributos.")
    if int(artifact["window_size"]) != 10:
        raise ModelSerializationError("O artefato deve usar janela de 10 registros.")
    transformer = artifact["window_transformer"]
    if (
        not isinstance(transformer, dict)
        or transformer.get("name") != "sliding_window"
        or transformer.get("flatten") is not True
    ):
        raise ModelSerializationError("A janela deve ser deslizante e achatada.")
    threshold = float(artifact["classification_threshold"])
    if not 0.0 < threshold < 1.0:
        raise ModelSerializationError("classification_threshold deve estar entre 0 e 1.")
    _validate_label_encoding(artifact["label_encoding"])


def predict_from_artifact(
    artifact_or_path: dict[str, Any] | str | Path,
    raw_rows: pd.DataFrame,
) -> dict[str, np.ndarray]:
    """Executa pré-processamento, seleção, janela e classificação."""
    artifact = (
        load_serialized_model(artifact_or_path)
        if isinstance(artifact_or_path, (str, Path))
        else artifact_or_path
    )
    validate_artifact(artifact)
    if not isinstance(raw_rows, pd.DataFrame):
        raise ModelSerializationError("A inferência exige DataFrame com esquema bruto.")

    raw_names = list(artifact["raw_feature_names"])
    missing = [name for name in raw_names if name not in raw_rows.columns]
    if missing:
        raise ModelSerializationError(
            "Entrada bruta não contém todas as features obrigatórias. "
            f"Primeiras ausentes: {missing[:10]}."
        )
    if len(raw_rows) < int(artifact["window_size"]):
        raise ModelSerializationError(
            f"Janela insuficiente: {len(raw_rows)} registros recebidos; esperados 10."
        )

    from src.features.fold_preprocessor import FoldPreprocessor

    preprocessor = FoldPreprocessor()
    preprocessor.__dict__.update(artifact["preprocessor_state"])
    raw = raw_rows[raw_names].copy()
    if int(pd.__version__.split(".", maxsplit=1)[0]) >= 3:
        for name in artifact["raw_numeric_feature_names"]:
            if pd.api.types.is_numeric_dtype(raw[name].dtype):
                raw[name] = raw[name].astype("Float64")
    transformed = preprocessor.transform(raw)
    selected_names = list(artifact["selected_feature_names"])
    missing_selected = [name for name in selected_names if name not in transformed]
    if missing_selected:
        raise ModelSerializationError(
            f"O pré-processador não produz o ranking congelado: {missing_selected}."
        )

    selected = transformed[selected_names].to_numpy(dtype=np.float32)
    window_size = int(artifact["window_size"])
    windows = np.lib.stride_tricks.sliding_window_view(
        selected, window_shape=window_size, axis=0
    )
    windows = np.moveaxis(windows, -1, 1).reshape(
        selected.shape[0] - window_size + 1,
        window_size * len(selected_names),
    )
    model = artifact["model"]
    probabilities = np.asarray(model.predict_proba(windows), dtype=float)
    classes = list(getattr(model, "classes_", []))
    if 1 not in classes:
        raise ModelSerializationError("O modelo não contém a classe positiva 1.")
    scores = probabilities[:, classes.index(1)]
    predictions = (
        scores >= float(artifact["classification_threshold"])
    ).astype(int)
    confidences = np.where(predictions == 1, scores, 1.0 - scores)
    labels = _decode_labels(predictions, artifact["label_encoding"])
    return {
        "predictions": predictions,
        "labels": labels,
        "confidence": confidences.astype(float),
        "attack_probability": scores.astype(float),
    }


def _feature_names(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ModelSerializationError(f"{field} deve ser uma lista não vazia.")
    names = [str(name) for name in value]
    if any(not name.strip() for name in names) or len(names) != len(set(names)):
        raise ModelSerializationError(f"{field} contém nomes inválidos ou duplicados.")
    return names


def _validate_label_encoding(encoding: Any) -> None:
    if not isinstance(encoding, dict) or "id_to_label" not in encoding:
        raise ModelSerializationError("label_encoding inválido.")
    mapping = encoding["id_to_label"]
    if not isinstance(mapping, dict):
        raise ModelSerializationError("id_to_label deve ser um dicionário.")
    if not ({0, 1}.issubset(mapping) or {"0", "1"}.issubset(mapping)):
        raise ModelSerializationError("id_to_label deve conter as classes 0 e 1.")


def _decode_labels(predictions: np.ndarray, encoding: dict[str, Any]) -> np.ndarray:
    mapping = encoding["id_to_label"]
    return np.asarray(
        [mapping.get(int(value), mapping.get(str(int(value)), str(value))) for value in predictions],
        dtype=object,
    )
