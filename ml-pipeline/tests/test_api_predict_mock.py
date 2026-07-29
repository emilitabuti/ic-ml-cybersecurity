"""
Testes do endpoint mock de predição — Story 4.4.

O mock permite que o dashboard consuma o contrato do /predict real antes do modelo
treinado existir.
"""

from datetime import datetime
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.api.main import app  # noqa: E402
from src.api.routes.predict import _reset_mock_prediction_cycle  # noqa: E402
from src.api.services import prediction_service  # noqa: E402


@pytest.fixture(autouse=True)
def clear_prediction_history(monkeypatch):
    monkeypatch.setenv("ALERT_EMAIL_ENABLED", "false")
    prediction_service.clear_prediction_history()
    yield
    prediction_service.clear_prediction_history()


def _parse_iso8601(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def test_predict_mock_returns_prediction_contract() -> None:
    _reset_mock_prediction_cycle()
    client = TestClient(app)

    response = client.post("/predict/mock")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert set(data) == {"prediction", "confidence", "model", "timestamp"}
    assert isinstance(data["prediction"], str)
    assert isinstance(data["confidence"], float)
    assert 0.0 <= data["confidence"] <= 1.0
    assert isinstance(data["model"], str)
    assert data["model"] == "mock-cyclic-v1"
    assert _parse_iso8601(data["timestamp"]).tzinfo is not None


def test_predict_mock_cycles_between_three_scenarios() -> None:
    _reset_mock_prediction_cycle()
    client = TestClient(app)

    responses = [client.post("/predict/mock").json() for _ in range(4)]

    assert [item["prediction"] for item in responses] == [
        "DDoS",
        "Suspicious Traffic",
        "Normal Traffic",
        "DDoS",
    ]
    assert responses[0]["confidence"] >= 0.90
    assert 0.70 <= responses[1]["confidence"] < 0.90
    assert responses[2]["confidence"] < 0.70
    assert responses[3]["confidence"] == responses[0]["confidence"]


def test_predict_mock_is_documented_in_openapi_schema() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi = response.json()
    assert "/predict/mock" in openapi["paths"]
    assert "post" in openapi["paths"]["/predict/mock"]
    assert (
        openapi["paths"]["/predict/mock"]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/PredictionResponse"
    )


def test_predict_mock_route_does_not_depend_on_unimplemented_ml_pipeline() -> None:
    route_source = (ROOT / "src/api/routes/predict.py").read_text()

    assert "src.features" not in route_source
    assert "src.training" not in route_source
    assert "src.models" not in route_source


def test_history_returns_prediction_service_data() -> None:
    event = {
        "prediction": "SYN Flood - High Intensity",
        "confidence": 0.95,
        "model": "random_forest",
        "timestamp": "2026-07-27T12:00:00Z",
    }
    prediction_service.append_prediction_history(event)
    client = TestClient(app)

    response = client.get("/history")

    assert response.status_code == 200
    assert response.json() == [event]


def test_history_demo_endpoint_pushes_events_to_dashboard_history(monkeypatch) -> None:
    _reset_mock_prediction_cycle()
    client = TestClient(app)

    event = {
        "prediction": "SYN Flood - High Intensity",
        "confidence": 0.95,
        "model": "syn-flood-dashboard-demo-v1",
        "timestamp": "2026-07-27T12:00:00Z",
    }

    push_response = client.post("/history/demo", json=event)
    history_response = client.get("/history")

    assert push_response.status_code == 200
    assert history_response.status_code == 200
    assert push_response.json() == [event]
    assert history_response.json() == [event]


def test_history_demo_sends_email_for_critical_alert(monkeypatch) -> None:
    monkeypatch.setenv("ALERT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("ALERT_EMAIL_TO", "analista@example.com")
    monkeypatch.setenv("ALERT_EMAIL_FROM", "dashboard@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "dashboard@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    _reset_mock_prediction_cycle()
    client = TestClient(app)

    event = {
        "prediction": "SYN Flood - High Intensity",
        "confidence": 0.95,
        "model": "syn-flood-dashboard-demo-v1",
        "timestamp": "2026-07-27T12:00:00Z",
    }

    with patch("src.api.services.email_notifications.smtplib.SMTP") as smtp:
        response = client.post("/history/demo", json=event)

    assert response.status_code == 200
    smtp.assert_called_once_with("smtp.example.com", 587, timeout=10)
    smtp.return_value.__enter__.return_value.starttls.assert_called_once()
    smtp.return_value.__enter__.return_value.login.assert_called_once_with(
        "dashboard@example.com", "secret"
    )
    sent_message = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
    assert sent_message["To"] == "analista@example.com"
    assert "SYN Flood - High Intensity" in sent_message.get_content()


def test_history_demo_does_not_send_email_for_non_critical_alert(monkeypatch) -> None:
    monkeypatch.setenv("ALERT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("ALERT_EMAIL_TO", "analista@example.com")
    monkeypatch.setenv("ALERT_EMAIL_FROM", "dashboard@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USERNAME", "dashboard@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    _reset_mock_prediction_cycle()
    client = TestClient(app)

    event = {
        "prediction": "SYN Flood - Low Intensity",
        "confidence": 0.77,
        "model": "syn-flood-dashboard-demo-v1",
        "timestamp": "2026-07-27T12:00:00Z",
    }

    with patch("src.api.services.email_notifications.smtplib.SMTP") as smtp:
        response = client.post("/history/demo", json=event)

    assert response.status_code == 200
    smtp.assert_not_called()


def test_history_demo_clear_preserves_real_prediction_history() -> None:
    _reset_mock_prediction_cycle()
    real_event = {
        "prediction": "BENIGN",
        "confidence": 0.91,
        "model": "random_forest",
        "timestamp": "2026-07-27T11:59:00Z",
    }
    prediction_service.append_prediction_history(real_event)
    client = TestClient(app)

    client.post(
        "/history/demo",
        json={
            "prediction": "SYN Flood - Low Intensity",
            "confidence": 0.77,
            "model": "syn-flood-dashboard-demo-v1",
            "timestamp": "2026-07-27T12:00:00Z",
        },
    )

    clear_response = client.delete("/history/demo")
    history_response = client.get("/history")

    assert clear_response.status_code == 200
    assert history_response.status_code == 200
    assert clear_response.json() == [real_event]
    assert history_response.json() == [real_event]
