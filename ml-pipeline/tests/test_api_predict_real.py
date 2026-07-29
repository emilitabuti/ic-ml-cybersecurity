from pathlib import Path
import sys

import joblib
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from src.api.main import app  # noqa: E402
from src.api.services import prediction_service  # noqa: E402
from src.models.model_serializer import serialize_model  # noqa: E402


@pytest.fixture
def client_with_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    artifact_path = _create_test_artifact(tmp_path)
    monkeypatch.setenv("MODEL_ARTIFACT_PATH", str(artifact_path))
    prediction_service.unload_model_for_tests()
    prediction_service.clear_prediction_history()

    with TestClient(app) as client:
        yield client

    prediction_service.clear_prediction_history()
    prediction_service.unload_model_for_tests()


def test_predict_returns_real_prediction(client_with_model: TestClient) -> None:
    response = client_with_model.post("/predict", json=_valid_payload())

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"prediction", "confidence", "model", "timestamp"}
    assert data["prediction"] in {"BENIGN", "Attack"}
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["model"] == "random_forest"
    assert data["timestamp"].endswith("Z")


def test_predict_returns_422_for_invalid_features(client_with_model: TestClient) -> None:
    payload = _valid_payload()
    del payload["features"][0]["bytes"]

    response = client_with_model.post("/predict", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_FEATURES"
    assert "bytes" in response.json()["detail"]


def test_model_info_returns_loaded_model_metadata(client_with_model: TestClient) -> None:
    response = client_with_model.get("/model/info")

    assert response.status_code == 200
    data = response.json()
    assert data["model_type"] == "random_forest"
    assert data["window_size"] == 5
    assert data["features"] == ["duration", "packets", "bytes"]
    assert data["trained_at"] is not None
    assert prediction_service.load_seconds() is not None
    assert prediction_service.load_seconds() <= 5.0


def test_health_returns_loaded_model_name(client_with_model: TestClient) -> None:
    response = client_with_model.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model"] == "random_forest"


def test_history_returns_recent_predictions(client_with_model: TestClient) -> None:
    first = client_with_model.post("/predict", json=_valid_payload()).json()
    second_payload = _valid_payload(offset=1.0)
    second = client_with_model.post("/predict", json=second_payload).json()

    response = client_with_model.get("/history")

    assert response.status_code == 200
    assert response.json() == [first, second]


def _create_test_artifact(tmp_path: Path) -> Path:
    X, y = _training_data()
    scaler = StandardScaler().fit(X)
    window_size = 5
    X_windows = _flatten_windows(scaler.transform(X), window_size)
    y_windows = y[window_size - 1 :]

    model = RandomForestClassifier(
        n_estimators=8,
        random_state=config.RANDOM_SEED,
        max_depth=3,
    )
    model.fit(X_windows, y_windows)

    model_path = tmp_path / "rf.joblib"
    scaler_path = tmp_path / "scaler.joblib"
    artifact_path = tmp_path / "model_rf.pkl"
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    serialize_model(
        model_path=model_path,
        scaler_path=scaler_path,
        output_path=artifact_path,
        model_type="random_forest",
        feature_names=["duration", "packets", "bytes"],
        window_size=window_size,
    )
    return artifact_path


def _valid_payload(offset: float = 0.0) -> dict[str, list[dict[str, float]]]:
    rows = []
    for index in range(5):
        rows.append(
            {
                "duration": offset + float(index) / 10,
                "packets": offset + 1.0 + float(index) / 10,
                "bytes": offset + 2.0 + float(index) / 10,
            }
        )
    return {"features": rows}


def _training_data() -> tuple[np.ndarray, np.ndarray]:
    X = np.array(
        [
            [0.0, 1.0, 2.0],
            [0.1, 1.1, 2.1],
            [0.2, 1.2, 2.2],
            [0.3, 1.3, 2.3],
            [0.4, 1.4, 2.4],
            [3.0, 4.0, 5.0],
            [3.1, 4.1, 5.1],
            [3.2, 4.2, 5.2],
            [3.3, 4.3, 5.3],
            [3.4, 4.4, 5.4],
        ],
        dtype=np.float32,
    )
    y = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1], dtype=int)
    return X, y


def _flatten_windows(X: np.ndarray, window_size: int) -> np.ndarray:
    windows = np.stack(
        [X[start : start + window_size] for start in range(X.shape[0] - window_size + 1)]
    )
    return windows.reshape(windows.shape[0], -1)
