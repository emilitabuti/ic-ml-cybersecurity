from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import APIRouter, Body

from src.api.schemas.prediction import (
    ModelInfoResponse,
    PredictionHistoryItem,
    PredictionResponse,
)
from src.api.services import prediction_service

router = APIRouter(tags=["prediction"])

MOCK_MODEL_NAME = "mock-cyclic-v1"
_MOCK_RESPONSES = (
    {"prediction": "DDoS", "confidence": 0.97},
    {"prediction": "Suspicious Traffic", "confidence": 0.82},
    {"prediction": "Normal Traffic", "confidence": 0.42},
)
_mock_index = 0
_mock_lock = Lock()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _reset_mock_prediction_cycle() -> None:
    global _mock_index

    with _mock_lock:
        _mock_index = 0


def _next_mock_prediction() -> dict[str, str | float]:
    global _mock_index

    with _mock_lock:
        response = _MOCK_RESPONSES[_mock_index]
        _mock_index = (_mock_index + 1) % len(_MOCK_RESPONSES)

    return {
        "prediction": response["prediction"],
        "confidence": response["confidence"],
        "model": MOCK_MODEL_NAME,
        "timestamp": _utc_timestamp(),
    }


@router.post(
    "/predict/mock",
    response_model=PredictionResponse,
    summary="Predição simulada para desenvolvimento paralelo do dashboard",
    description=(
        "Retorna uma predição simulada no mesmo formato do endpoint /predict real, "
        "sem carregar modelos treinados ou executar feature engineering."
    ),
)
def predict_mock() -> PredictionResponse:
    return PredictionResponse(**_next_mock_prediction())


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Predição real com o modelo carregado no startup",
)
def predict(payload: Any = Body(...)) -> PredictionResponse:
    return PredictionResponse(**prediction_service.predict(payload))


@router.get(
    "/model/info",
    response_model=ModelInfoResponse,
    summary="Metadados do modelo carregado",
)
def model_info() -> ModelInfoResponse:
    return ModelInfoResponse(**prediction_service.model_info())


@router.get(
    "/history",
    response_model=list[PredictionHistoryItem],
    summary="Últimas predições em memória",
)
def history() -> list[PredictionHistoryItem]:
    return [
        PredictionHistoryItem(**item)
        for item in prediction_service.prediction_history()
    ]
