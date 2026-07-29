import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from fastapi import APIRouter

from src.api.schemas.prediction import PredictionResponse
from src.api.services.email_notifications import send_critical_alert_email

router = APIRouter(tags=["prediction"])

MOCK_MODEL_NAME = "mock-cyclic-v1"
ISABELA_SYN_FLOOD_HISTORY_FILE_ENV = "ISABELA_SYN_FLOOD_HISTORY_FILE"
_MOCK_RESPONSES = (
    {"prediction": "DDoS", "confidence": 0.97},
    {"prediction": "Suspicious Traffic", "confidence": 0.82},
    {"prediction": "Normal Traffic", "confidence": 0.42},
)
_MAX_MOCK_HISTORY = 100
_MAX_DEMO_HISTORY = 100
_mock_index = 0
_mock_lock = Lock()
_mock_history: list[PredictionResponse] = []
_demo_history: list[PredictionResponse] = []
_auto_mock_history_enabled = True


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _reset_mock_prediction_cycle() -> None:
    global _auto_mock_history_enabled, _mock_index

    with _mock_lock:
        _mock_index = 0
        _mock_history.clear()
        _demo_history.clear()
        _auto_mock_history_enabled = True


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


@router.post(
    "/history/demo",
    response_model=list[PredictionResponse],
    summary="Injeta uma predicao simulada no historico do dashboard",
    description=(
        "Recebe uma predicao ja simulada e a adiciona ao historico em memoria. "
        "Este endpoint existe para demonstracoes controladas do dashboard sem "
        "executar ataques reais e sem depender do modelo final."
    ),
)
def push_demo_history_event(prediction: PredictionResponse) -> list[PredictionResponse]:
    with _mock_lock:
        _demo_history.insert(0, prediction)
        del _demo_history[_MAX_DEMO_HISTORY:]
        history = list(_demo_history)

    send_critical_alert_email(prediction)
    return history


@router.delete(
    "/history/demo",
    response_model=list[PredictionResponse],
    summary="Limpa predicoes simuladas de demonstracao",
)
def clear_demo_history() -> list[PredictionResponse]:
    global _auto_mock_history_enabled

    with _mock_lock:
        _demo_history.clear()
        _mock_history.clear()
        _auto_mock_history_enabled = False
        return []


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

    with _mock_lock:
        if _demo_history:
            return list(_demo_history)
        if not _auto_mock_history_enabled:
            return []

    prediction = PredictionResponse(**_next_mock_prediction())

    with _mock_lock:
        _mock_history.insert(0, prediction)
        del _mock_history[_MAX_MOCK_HISTORY:]
        return list(_mock_history)
