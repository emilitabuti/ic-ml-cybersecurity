"""Carregamento opcional de eventos reais para o historico do dashboard."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from src.api.services import prediction_service
from src.evaluation.scenarios.send_real_predictions_to_api import (
    DEFAULT_EVENTS_FILE,
    build_window,
)

logger = logging.getLogger(__name__)

AUTOLOAD_ENV = "DASHBOARD_AUTOLOAD_REAL_EVENTS"
AUTOLOAD_FILE_ENV = "DASHBOARD_AUTOLOAD_EVENTS_FILE"
AUTOLOAD_LIMIT_ENV = "DASHBOARD_AUTOLOAD_LIMIT"
DEFAULT_AUTOLOAD_LIMIT = 20


def autoload_dashboard_history_if_enabled() -> int:
    if not _env_enabled(AUTOLOAD_ENV):
        return 0

    if prediction_service.prediction_history():
        logger.info("Historico do dashboard ja possui eventos; autoload ignorado.")
        return 0

    events_file = Path(os.getenv(AUTOLOAD_FILE_ENV, str(DEFAULT_EVENTS_FILE)))
    limit = int(os.getenv(AUTOLOAD_LIMIT_ENV, str(DEFAULT_AUTOLOAD_LIMIT)))
    return load_dashboard_history(events_file=events_file, limit=limit)


def load_dashboard_history(*, events_file: Path, limit: int) -> int:
    events = _load_events(events_file)
    model_info = prediction_service.model_info()
    feature_names = list(model_info["features"])
    window_size = int(model_info["window_size"])

    loaded = 0
    for event in events[:limit]:
        source_prediction = str(event.get("prediction", ""))
        payload = {
            "source_prediction": source_prediction,
            "features": build_window(
                feature_names,
                window_size=window_size,
                event=event,
            ),
        }
        prediction_service.predict(payload)
        loaded += 1

    logger.info("Eventos reais carregados para o dashboard: %d", loaded)
    return loaded


def _load_events(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.resolve().read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Arquivo de eventos invalido: {path}")
    return [item for item in data if isinstance(item, dict)]


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
