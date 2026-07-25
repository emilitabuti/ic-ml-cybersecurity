"""
Testes do endpoint mock de predição — Story 4.4.

O mock permite que o dashboard consuma o contrato do /predict real antes do modelo
treinado existir.
"""

from datetime import datetime
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.api.main import app  # noqa: E402
from src.api.routes.predict import _reset_mock_prediction_cycle  # noqa: E402


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
