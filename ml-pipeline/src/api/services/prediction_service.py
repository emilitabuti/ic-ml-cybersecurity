"""Serviço de inferência e estado em memória da API."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import logging
import math
from numbers import Real
import os
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any

import numpy as np

import config
from src.models.model_serializer import (
    ModelSerializationError,
    load_serialized_model,
    predict_from_artifact,
)

logger = logging.getLogger(__name__)

LOAD_TIME_LIMIT_SECONDS = 5.0
HISTORY_LIMIT = 100


class PredictionError(RuntimeError):
    """Erro tipado do domínio de predição."""

    code = "PREDICTION_ERROR"


class ModelNotLoadedError(PredictionError):
    """Modelo não está disponível para inferência."""

    code = "MODEL_NOT_LOADED"


class InvalidFeaturesError(PredictionError):
    """Payload de features incompatível com o modelo carregado."""

    code = "INVALID_FEATURES"


_model_lock = Lock()
_history_lock = Lock()
_artifact: dict[str, Any] | None = None
_artifact_path: Path | None = None
_load_seconds: float | None = None
_history: deque[dict[str, str | float]] = deque(maxlen=HISTORY_LIMIT)


def load_model_once(path: str | Path | None = None, *, force: bool = False) -> None:
    """Carrega o artefato serializado uma vez por processo da API."""
    global _artifact, _artifact_path, _load_seconds

    resolved_path = _resolve_model_path(path)
    with _model_lock:
        if _artifact is not None and _artifact_path == resolved_path and not force:
            logger.debug("Modelo já carregado em memória: %s", resolved_path)
            return

        start = perf_counter()
        artifact = load_serialized_model(resolved_path)
        elapsed = perf_counter() - start
        if elapsed > LOAD_TIME_LIMIT_SECONDS:
            logger.warning(
                "Modelo carregou acima do limite de %.1fs: %.3fs",
                LOAD_TIME_LIMIT_SECONDS,
                elapsed,
            )
        else:
            logger.info("Modelo carregado em %.3fs: %s", elapsed, resolved_path)

        _artifact = artifact
        _artifact_path = resolved_path
        _load_seconds = elapsed


def predict(payload: Any) -> dict[str, str | float]:
    artifact = _get_loaded_artifact()
    X = _payload_to_feature_array(payload, artifact)

    try:
        output = predict_from_artifact(artifact, X)
    except ModelSerializationError as exc:
        raise InvalidFeaturesError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Falha durante inferência")
        raise PredictionError("Falha ao executar predição.") from exc

    prediction = str(output["labels"][-1])
    confidence = float(output["confidence"][-1])
    response = {
        "prediction": prediction,
        "confidence": confidence,
        "model": str(artifact["model_type"]),
        "timestamp": _utc_timestamp(),
    }
    _append_history(response)
    return response


def model_info() -> dict[str, Any]:
    artifact = _get_loaded_artifact()
    return {
        "model_type": str(artifact["model_type"]),
        "window_size": int(artifact["window_size"]),
        "features": list(artifact["feature_names"]),
        "trained_at": artifact.get("trained_at") or artifact.get("created_at"),
    }


def prediction_history() -> list[dict[str, str | float]]:
    with _history_lock:
        return list(_history)


def clear_prediction_history() -> None:
    with _history_lock:
        _history.clear()


def unload_model_for_tests() -> None:
    global _artifact, _artifact_path, _load_seconds

    with _model_lock:
        _artifact = None
        _artifact_path = None
        _load_seconds = None


def load_seconds() -> float | None:
    return _load_seconds


def _get_loaded_artifact() -> dict[str, Any]:
    if _artifact is None:
        raise ModelNotLoadedError("Modelo serializado ainda não foi carregado.")
    return _artifact


def _payload_to_feature_array(payload: Any, artifact: dict[str, Any]) -> np.ndarray:
    rows = _extract_rows(payload)
    feature_names = list(artifact["feature_names"])
    window_size = int(artifact["window_size"])

    if len(rows) < window_size:
        raise InvalidFeaturesError(
            "Janela insuficiente para predição: "
            f"{len(rows)} registros recebidos, window_size={window_size}."
        )

    values: list[list[float]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidFeaturesError(
                "Cada registro de features deve ser um objeto JSON; "
                f"índice inválido: {row_index}."
            )

        missing = [name for name in feature_names if name not in row]
        if missing:
            raise InvalidFeaturesError(
                "Features obrigatórias ausentes: " + ", ".join(missing[:10])
            )

        values.append([
            _coerce_numeric_feature(row[name], name=name, row_index=row_index)
            for name in feature_names
        ])

    return np.asarray(values, dtype=np.float32)


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and "features" in payload:
        features = payload["features"]
    else:
        features = payload

    if isinstance(features, list):
        if not features:
            raise InvalidFeaturesError("features deve conter ao menos uma janela.")
        return features

    if isinstance(features, dict):
        if features and all(isinstance(value, list) for value in features.values()):
            lengths = {len(value) for value in features.values()}
            if len(lengths) != 1:
                raise InvalidFeaturesError(
                    "Features em formato colunar devem ter listas com o mesmo tamanho."
                )
            return [
                {name: values[index] for name, values in features.items()}
                for index in range(next(iter(lengths)))
            ]
        return [features]

    raise InvalidFeaturesError(
        "Payload inválido: envie {'features': [objetos_de_features]}."
    )


def _coerce_numeric_feature(value: Any, *, name: str, row_index: int) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise InvalidFeaturesError(
            f"Feature '{name}' no registro {row_index} deve ser numérica."
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidFeaturesError(
            f"Feature '{name}' no registro {row_index} deve ser finita."
        )
    return numeric


def _append_history(item: dict[str, str | float]) -> None:
    with _history_lock:
        _history.append(item)


def _resolve_model_path(path: str | Path | None = None) -> Path:
    explicit = path or os.getenv("MODEL_ARTIFACT_PATH")
    if explicit:
        return _resolve_project_relative_path(Path(explicit))

    default_path = _resolve_project_relative_path(
        Path(config.MODEL_PATH) / "model_rf.pkl"
    )
    if default_path.exists():
        return default_path

    candidates = sorted(
        _resolve_project_relative_path(Path(config.MODEL_PATH)).glob("model_*.pkl")
    )
    if candidates:
        return candidates[0]

    raise FileNotFoundError(
        f"Artefato de modelo serializado não encontrado: {default_path}."
    )


def _resolve_project_relative_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return _project_root() / path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
