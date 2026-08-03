from pathlib import Path

import joblib
import pandas as pd
import pytest

from src.models.model_serializer import (
    ARTIFACT_VERSION,
    ModelSerializationError,
    load_serialized_model,
    predict_from_artifact,
    validate_artifact,
)
from tests.temporal_artifact_factory import build_test_artifact


def test_canonical_artifact_loads_and_predicts_raw_window(tmp_path: Path) -> None:
    path, rows = build_test_artifact(tmp_path / "model.pkl")
    artifact = load_serialized_model(path)
    output = predict_from_artifact(artifact, pd.DataFrame(rows))

    assert artifact["artifact_version"] == ARTIFACT_VERSION
    assert artifact["model_type"] == "random_forest"
    assert len(artifact["selected_feature_names"]) == 30
    assert output["predictions"].shape == (1,)
    assert output["attack_probability"].shape == (1,)
    assert output["labels"][0] in {"BENIGN", "Attack"}


def test_canonical_artifact_rejects_missing_raw_feature(tmp_path: Path) -> None:
    path, rows = build_test_artifact(tmp_path / "model.pkl")
    artifact = load_serialized_model(path)
    frame = pd.DataFrame(rows).drop(columns=["f0"])

    with pytest.raises(ModelSerializationError, match="ausentes"):
        predict_from_artifact(artifact, frame)


def test_incomplete_artifact_is_not_supported(tmp_path: Path) -> None:
    path = tmp_path / "incomplete.pkl"
    joblib.dump(
        {
            "artifact_version": "1.0",
            "model_type": "random_forest",
            "model": object(),
        },
        path,
    )

    with pytest.raises(ModelSerializationError, match="componente"):
        load_serialized_model(path)


def test_validator_requires_exactly_thirty_selected_features(tmp_path: Path) -> None:
    path, _ = build_test_artifact(tmp_path / "model.pkl")
    artifact = joblib.load(path)
    artifact["selected_feature_names"] = artifact["selected_feature_names"][:-1]
    artifact["feature_names"] = artifact["feature_names"][:-1]

    with pytest.raises(ModelSerializationError, match="30 atributos"):
        validate_artifact(artifact)
