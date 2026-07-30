"""Testes do filtro estrito e da divisão temporal."""

from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from src.data.temporal_splitter import (
    event_aware_purged_split,
    filter_attack_free_history,
    generate_strict_temporal_split_artifacts,
)
from src.data.prospective.temporal_audit import TemporalAuditError


BASE = 1_421_927_400


def _flows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_file": ["part-a"] * 4,
            "Stime": [BASE, BASE + 50, BASE + 100, BASE + 500],
            "Ltime": [BASE, BASE + 50, BASE + 100, BASE + 500],
            "Binary_Label": [0, 1, 0, 0],
        }
    )


def _filter_labels() -> pd.DataFrame:
    rows = []
    for timestamp in (BASE + 100, BASE + 170, BASE + 171):
        for horizon in (5, 60):
            rows.append(
                {
                    "source_file": "part-a",
                    "Stime": timestamp,
                    "Prediction_Horizon_Seconds": horizon,
                    "Future_Attack_Label": 0,
                    "Seconds_To_Attack": None,
                    "Next_Attack_Onset": None,
                    "Next_Attack_Event_ID": None,
                }
            )
    return pd.DataFrame(rows)


def _split_frame() -> pd.DataFrame:
    rows = []
    event_times = [BASE + offset for offset in (1000, 2000, 3000, 4000, 5000)]
    for timestamp in range(BASE + 800, BASE + 5201, 20):
        next_events = [event for event in event_times if event > timestamp]
        onset = next_events[0] if next_events else None
        event_id = (
            f"E{event_times.index(onset) + 1}" if onset is not None else None
        )
        seconds = onset - timestamp if onset is not None else None
        for horizon in (5, 60):
            rows.append(
                {
                    "source_file": "part-a",
                    "Stime": timestamp,
                    "Prediction_Horizon_Seconds": horizon,
                    "Future_Attack_Label": int(
                        seconds is not None and 0 < seconds <= horizon
                    ),
                    "Seconds_To_Attack": seconds,
                    "Next_Attack_Onset": onset,
                    "Next_Attack_Event_ID": event_id,
                    "Strict_History_Attack_Free": True,
                    "Strict_Lookback_Seconds": 120,
                }
            )
    return pd.DataFrame(rows)


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_strict_filter_removes_completed_prior_attack() -> None:
    strict, audit = filter_attack_free_history(
        _filter_labels(),
        _flows(),
        lookback_seconds=120,
    )

    assert set(strict["Stime"]) == {BASE + 170, BASE + 171}
    assert audit["excluded_temporal_units"] == 1
    assert strict["Strict_History_Attack_Free"].all()


def test_strict_window_is_open_at_lower_boundary() -> None:
    labels = _filter_labels().loc[
        _filter_labels()["Stime"].eq(BASE + 170)
    ]
    strict, _ = filter_attack_free_history(
        labels,
        _flows(),
        lookback_seconds=120,
    )

    assert len(strict) == 2


def test_event_aware_split_is_chronological_and_purged() -> None:
    split, audit = event_aware_purged_split(
        _split_frame(),
        purge_seconds=180,
    )
    bounds = {
        name: (
            split.loc[split["Split"].eq(name), "Stime"].min(),
            split.loc[split["Split"].eq(name), "Stime"].max(),
        )
        for name in ("train", "validation", "test")
    }

    assert bounds["validation"][0] - bounds["train"][1] >= 180
    assert bounds["test"][0] - bounds["validation"][1] >= 180
    assert audit["event_allocation"] == {
        "total": 5,
        "train": 3,
        "validation": 1,
        "test": 1,
    }


def test_positive_events_never_cross_partitions() -> None:
    split, _ = event_aware_purged_split(
        _split_frame(),
        purge_seconds=180,
    )
    event_splits = (
        split.loc[split["Future_Attack_Label"].eq(1)]
        .groupby("Next_Attack_Event_ID", observed=True)["Split"]
        .nunique()
    )

    assert (event_splits == 1).all()


def test_requires_at_least_three_strict_events() -> None:
    frame = _split_frame()
    frame = frame.loc[frame["Next_Attack_Event_ID"].isin(["E1", "E2"])]

    with pytest.raises(TemporalAuditError, match="três eventos"):
        event_aware_purged_split(frame, purge_seconds=180)


def test_artifact_generation_preserves_inputs(tmp_path: Path) -> None:
    flows_path = tmp_path / "flows.parquet"
    labels_path = tmp_path / "labels.parquet"
    features_path = tmp_path / "features.parquet"
    output_path = tmp_path / "strict.parquet"
    report_path = tmp_path / "strict.json"
    split_frame = _split_frame()
    flows = pd.DataFrame(
        {
            "source_file": ["part-a"],
            "Stime": [BASE],
            "Ltime": [BASE],
            "Binary_Label": [0],
        }
    )
    features = split_frame[["source_file", "Stime"]].drop_duplicates()
    features["feature_120s"] = 1.0
    flows.to_parquet(flows_path, index=False)
    split_frame.to_parquet(labels_path, index=False)
    features.to_parquet(features_path, index=False)
    hashes = {
        path: _hash(path)
        for path in (flows_path, labels_path, features_path)
    }

    report = generate_strict_temporal_split_artifacts(
        flows_path,
        labels_path,
        features_path,
        output_path,
        report_path,
    )

    assert all(_hash(path) == digest for path, digest in hashes.items())
    assert output_path.exists()
    assert report["validation"]["purge_respected"] is True
    assert (
        report["scientific_interpretation"]["class_viability"][
            "adequate_for_reliable_evaluation"
        ]
        is False
    )
    assert "partições" in report_path.read_text(encoding="utf-8")


def test_refuses_implicit_overwrite(tmp_path: Path) -> None:
    flows_path = tmp_path / "flows.parquet"
    labels_path = tmp_path / "labels.parquet"
    features_path = tmp_path / "features.parquet"
    output_path = tmp_path / "strict.parquet"
    report_path = tmp_path / "strict.json"
    _flows().to_parquet(flows_path, index=False)
    _filter_labels().to_parquet(labels_path, index=False)
    pd.DataFrame(
        {"source_file": ["part-a"], "Stime": [BASE], "x": [1.0]}
    ).to_parquet(features_path, index=False)
    output_path.write_bytes(b"existing")

    with pytest.raises(FileExistsError, match="--overwrite"):
        generate_strict_temporal_split_artifacts(
            flows_path,
            labels_path,
            features_path,
            output_path,
            report_path,
        )
