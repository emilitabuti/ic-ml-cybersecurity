import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

import config
from src.models.model_serializer import (
    ModelSerializationError,
    load_serialized_model,
    predict_from_artifact,
    select_winning_model,
    serialize_model,
)


def test_serialize_deserialize_and_predict_reconstructed_artifact(
    tmp_path: Path,
) -> None:
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

    output_path = serialize_model(
        model_path=model_path,
        scaler_path=scaler_path,
        output_path=artifact_path,
        model_type="random_forest",
        feature_names=["duration", "packets", "bytes"],
        window_size=window_size,
    )

    artifact = load_serialized_model(output_path)
    prediction = predict_from_artifact(artifact, X[:window_size])

    assert output_path == artifact_path
    assert artifact["model_type"] == "random_forest"
    assert artifact["scaler"] is not None
    assert artifact["window_size"] == window_size
    assert artifact["label_encoding"]["id_to_label"][0] == "BENIGN"
    assert prediction["predictions"].shape == (1,)
    assert prediction["labels"][0] in {"BENIGN", "Attack"}
    assert 0.0 <= prediction["confidence"][0] <= 1.0


def test_artifact_joblib_load_does_not_require_project_source(
    tmp_path: Path,
) -> None:
    X, y = _training_data()
    scaler = StandardScaler().fit(X)
    model = RandomForestClassifier(
        n_estimators=4,
        random_state=config.RANDOM_SEED,
        max_depth=2,
    )
    model.fit(_flatten_windows(scaler.transform(X), 5), y[4:])

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
        window_size=5,
    )

    script = (
        "import joblib; "
        f"artifact = joblib.load({str(artifact_path)!r}); "
        "assert artifact['model_type'] == 'random_forest'; "
        "assert artifact['model'].predict([[0.0] * 15]).shape == (1,); "
        "assert artifact['scaler'] is not None"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_load_fails_with_descriptive_error_when_pipeline_component_missing(
    tmp_path: Path,
) -> None:
    broken_artifact_path = tmp_path / "broken.pkl"
    joblib.dump(
        {
            "artifact_version": "1.0",
            "model_type": "random_forest",
            "model_format": "sklearn_joblib",
            "model": object(),
            "window_size": 5,
            "window_transformer": {"name": "sliding_window", "flatten": True},
            "feature_names": ["duration"],
            "label_encoding": {"id_to_label": {0: "BENIGN", 1: "Attack"}},
        },
        broken_artifact_path,
    )

    with pytest.raises(ModelSerializationError, match="scaler"):
        load_serialized_model(broken_artifact_path)


def test_select_winning_model_uses_best_metrics_then_f1(tmp_path: Path) -> None:
    comparison_csv = tmp_path / "comparison_metrics.csv"
    comparison_csv.write_text(
        "\n".join(
            [
                "model_type,algorithm,f1,auc_roc,precision,recall,fpr,best_metrics",
                "decision_tree,DecisionTreeClassifier,0.9480 +/- 0.0004,"
                "0.9832 +/- 0.0006,0.9513 +/- 0.0012,0.9446 +/- 0.0016,"
                "0.0019 +/- 0.0001,recall",
                "random_forest,RandomForestClassifier,0.9514 +/- 0.0008,"
                "0.9996 +/- 0.0000,0.9598 +/- 0.0019,0.9432 +/- 0.0014,"
                '0.0016 +/- 0.0001,"f1, auc_roc, precision, fpr"',
            ]
        ),
        encoding="utf-8",
    )

    assert select_winning_model(comparison_csv) == "random_forest"


def _training_data() -> tuple[np.ndarray, np.ndarray]:
    X = np.array(
        [
            [0.0, 1.0, 1.0],
            [0.1, 1.2, 1.1],
            [0.2, 1.1, 1.3],
            [0.3, 1.4, 1.2],
            [0.4, 1.3, 1.4],
            [3.0, 4.0, 4.0],
            [3.1, 4.2, 4.1],
            [3.2, 4.1, 4.3],
            [3.3, 4.4, 4.2],
            [3.4, 4.3, 4.4],
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
