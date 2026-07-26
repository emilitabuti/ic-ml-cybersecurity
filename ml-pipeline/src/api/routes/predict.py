import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from fastapi import APIRouter

from src.api.schemas.prediction import PredictionResponse

router = APIRouter(tags=["prediction"])

MOCK_MODEL_NAME = "mock-cyclic-v1"
ISABELA_SYN_FLOOD_HISTORY_FILE_ENV = "ISABELA_SYN_FLOOD_HISTORY_FILE"
_MOCK_RESPONSES = (
    {"prediction": "DDoS", "confidence": 0.97},
    {"prediction": "Suspicious Traffic", "confidence": 0.82},
    {"prediction": "Normal Traffic", "confidence": 0.42},
)
_MAX_MOCK_HISTORY = 100
_mock_index = 0
_mock_lock = Lock()
_mock_history: list[PredictionResponse] = []


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _reset_mock_prediction_cycle() -> None:
    global _mock_index

    with _mock_lock:
        _mock_index = 0
        _mock_history.clear()


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


def _load_external_history_from_env() -> list[PredictionResponse] | None:
    history_file = os.getenv(ISABELA_SYN_FLOOD_HISTORY_FILE_ENV)
    if not history_file:
        return None

    path = Path(history_file)
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de historico simulado nao encontrado: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("O historico simulado deve ser uma lista de predicoes.")

    # O dashboard ja espera o contrato PredictionResponse usado por /history.
    return [PredictionResponse(**item) for item in reversed(data)]


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


@router.get(
    "/history",
    response_model=list[PredictionResponse],
    summary="Histórico mock de predições para polling do dashboard",
    description=(
        "Gera uma nova predição simulada e retorna o histórico em memória para "
        "permitir desenvolvimento do dashboard via GET /history sem modelo real."
    ),
)
def history_mock() -> list[PredictionResponse]:
    external_history = _load_external_history_from_env()
    if external_history is not None:
        return external_history

    prediction = PredictionResponse(**_next_mock_prediction())

    with _mock_lock:
        _mock_history.insert(0, prediction)
        del _mock_history[_MAX_MOCK_HISTORY:]
        return list(_mock_history)
