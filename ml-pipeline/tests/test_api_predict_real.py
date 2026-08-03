from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.services import prediction_service
from tests.temporal_artifact_factory import build_test_artifact


@pytest.fixture
def client_with_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    artifact_path, rows = build_test_artifact(tmp_path / "model.pkl")
    monkeypatch.setenv("MODEL_ARTIFACT_PATH", str(artifact_path))
    monkeypatch.setenv("DASHBOARD_AUTOLOAD_REAL_EVENTS", "false")
    prediction_service.unload_model_for_tests()
    prediction_service.clear_prediction_history()
    with TestClient(app) as client:
        yield client, rows
    prediction_service.clear_prediction_history()
    prediction_service.unload_model_for_tests()


def test_predict_runs_canonical_raw_pipeline(client_with_model) -> None:
    client, rows = client_with_model
    response = client.post("/predict", json={"features": rows})

    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] in {"BENIGN", "Attack"}
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["model"] == "random_forest"


def test_predict_rejects_missing_raw_feature(client_with_model) -> None:
    client, rows = client_with_model
    del rows[0]["f0"]
    response = client.post("/predict", json={"features": rows})

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_FEATURES"
    assert "f0" in response.json()["detail"]


def test_model_info_exposes_only_canonical_schema(client_with_model) -> None:
    client, _ = client_with_model
    response = client.get("/model/info")

    assert response.status_code == 200
    data = response.json()
    assert data["model_type"] == "random_forest"
    assert data["window_size"] == 10
    assert data["artifact_version"] == "2.0"
    assert data["input_schema"] == "raw"
    assert len(data["selected_features"]) == 30
    assert prediction_service.load_seconds() <= 5.0


def test_health_and_history_use_canonical_model(client_with_model) -> None:
    client, rows = client_with_model
    health = client.get("/health")
    predicted = client.post("/predict", json={"features": rows}).json()
    history = client.get("/history")

    assert health.status_code == 200
    assert health.json()["model"] == "random_forest"
    assert history.json() == [predicted]


def test_source_prediction_is_preserved(client_with_model) -> None:
    client, rows = client_with_model
    response = client.post(
        "/predict",
        json={
            "features": rows,
            "source_prediction": "SYN Flood - Low Intensity",
        },
    )
    assert response.status_code == 200
    assert response.json()["source_prediction"] == "SYN Flood - Low Intensity"
