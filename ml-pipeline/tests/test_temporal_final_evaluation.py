from __future__ import annotations

import numpy as np
import pandas as pd

from src.training.temporal_final_evaluation import (
    _build_test_result,
    _ensure_writable_numeric_conversion,
    _window_batch_count,
)


def test_window_batch_count_respects_session_and_source_boundaries() -> None:
    frame = pd.DataFrame(
        {
            "temporal_session": [0] * 6 + [1] * 5,
            "source_file": ["a"] * 3 + ["b"] * 3 + ["c"] * 5,
        }
    )
    assert _window_batch_count(frame, window_size=3, batch_size=2) == 4


def test_build_test_result_reports_global_session_and_attack_metrics(tmp_path) -> None:
    predictions = pd.DataFrame(
        {
            "target_record_id": [1, 2, 3, 4],
            "temporal_session": [2, 2, 2, 2],
            "source_file": ["a"] * 4,
            "attack_type": ["Normal", "Normal", "DoS", "Exploits"],
            "y_true": [0, 0, 1, 1],
            "y_pred": [0, 1, 1, 0],
            "y_score": [0.1, 0.7, 0.9, 0.2],
        }
    )
    path = tmp_path / "predictions.parquet"
    predictions.to_parquet(path, index=False)
    training = {
        "variant": "top_10",
        "feature_count": 10,
        "feature_names": [f"f{i}" for i in range(10)],
        "feature_names_sha256": "hash",
        "fit_seconds": 1.0,
        "artifact_size_bytes": 123,
    }

    result = _build_test_result(
        "decision_tree",
        training,
        predictions,
        path,
        inference_seconds=0.5,
        protocol_sha256="protocol",
    )

    assert result["metrics"]["f1"] == 0.5
    assert result["confusion_matrix"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 1}
    assert set(result["metrics_by_attack_type"]) == {"DoS", "Exploits"}
    assert result["metrics_by_session"]["2"]["f1"] == 0.5
    assert result["selection_or_tuning_on_test"] is False


def test_writable_conversion_preserves_values() -> None:
    frame = pd.DataFrame(
        {
            "record_id": [1, 2],
            "split": ["train", "train"],
            "dur": [1.25, 2.5],
            "proto": ["tcp", "udp"],
        }
    )
    converted = _ensure_writable_numeric_conversion(frame)
    assert converted["dur"].astype(float).tolist() == [1.25, 2.5]
    assert converted["record_id"].tolist() == [1, 2]
