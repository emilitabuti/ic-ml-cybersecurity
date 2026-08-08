from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from src.features.fold_preprocessor import FoldPreprocessor
from src.models.model_serializer import (
    ARTIFACT_VERSION,
    DEFAULT_LABEL_ENCODING,
    PIPELINE_KIND,
)


def build_test_artifact(path: Path) -> tuple[Path, list[dict[str, object]]]:
    rows = 24
    raw = pd.DataFrame(
        {
            **{
                f"f{index}": np.linspace(index, index + 1, rows, dtype=np.float64)
                for index in range(30)
            },
            "proto": ["tcp"] * 12 + ["udp"] * 12,
            "record_id": np.arange(rows),
            "split": ["train"] * rows,
            "Binary_Label": [0] * 12 + [1] * 12,
        }
    )
    preprocessor = FoldPreprocessor().fit(raw)
    transformed = preprocessor.transform(raw)
    selected = [f"f{index}" for index in range(30)]
    values = transformed[selected].to_numpy(dtype=np.float32)
    windows = np.stack([values[index : index + 10] for index in range(15)]).reshape(15, 300)
    model = RandomForestClassifier(n_estimators=8, max_depth=3, random_state=42)
    model.fit(windows, raw["Binary_Label"].to_numpy()[9:])
    raw_names = [*preprocessor.numeric_columns_, *preprocessor.categorical_columns_]
    artifact = {
        "artifact_version": ARTIFACT_VERSION,
        "pipeline_kind": PIPELINE_KIND,
        "created_at": "2026-08-01T00:00:00+00:00",
        "model_type": "random_forest",
        "model_format": "sklearn_joblib",
        "model": model,
        "preprocessor_state": preprocessor.__dict__,
        "raw_feature_names": raw_names,
        "raw_numeric_feature_names": list(preprocessor.numeric_columns_),
        "raw_categorical_feature_names": list(preprocessor.categorical_columns_),
        "selected_feature_names": selected,
        "feature_names": selected,
        "window_size": 10,
        "window_transformer": {
            "name": "sliding_window",
            "flatten": True,
            "label_strategy": "last_record",
        },
        "label_encoding": DEFAULT_LABEL_ENCODING,
        "classification_threshold": 0.5,
        "protocol_sha256": "protocol-test",
        "final_metrics_sha256": "metrics-test",
    }
    joblib.dump(artifact, path)
    payload = raw.iloc[:10][raw_names].to_dict(orient="records")
    return path, payload
