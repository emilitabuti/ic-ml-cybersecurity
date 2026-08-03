"""Testes do split temporal auditável para detecção."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.detection_temporal_splitter import (
    assign_record_ids,
    assign_splits_and_purge,
    identify_natural_sessions,
    materialize_detection_temporal_split,
    stable_temporal_sort,
    window_integrity_summary,
)


def _synthetic_sessions() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    starts = [100, 5_000, 10_000]
    attack_types = ["Analysis", "DoS", "Generic"]
    for session, start in enumerate(starts):
        for offset in range(12):
            label = offset % 2
            rows.append(
                {
                    "Stime": start + offset,
                    "Ltime": start + offset,
                    "source_file": f"part-{session}",
                    "Binary_Label": label,
                    "attack_cat": attack_types[session] if label else "BENIGN",
                    "feature": float(session * 100 + offset),
                }
            )
    frame = pd.DataFrame(rows)
    return frame.sample(frac=1.0, random_state=42).reset_index(drop=True)


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_record_id_is_assigned_before_stable_temporal_sort() -> None:
    original = _synthetic_sessions()
    identified = assign_record_ids(original)
    sorted_df = stable_temporal_sort(identified)

    assert identified["record_id"].tolist() == list(range(len(original)))
    assert sorted_df["record_id"].is_unique
    assert sorted_df["Stime"].is_monotonic_increasing
    for _, row in sorted_df.iterrows():
        original_row = original.iloc[int(row["record_id"])]
        assert row["feature"] == original_row["feature"]


def test_natural_sessions_and_purge_preserve_chronology() -> None:
    sorted_df = stable_temporal_sort(assign_record_ids(_synthetic_sessions()))
    session_df, cuts = identify_natural_sessions(sorted_df, gap_seconds=3_600)
    partitions, audit = assign_splits_and_purge(session_df, window_size=3)

    assert cuts.tolist() == [5_000, 10_000]
    assert session_df["temporal_session"].nunique() == 3
    assert len(partitions["train"]) == 10
    assert len(partitions["validation"]) == 8
    assert len(partitions["test"]) == 10
    assert audit["purge_per_boundary_side_rows"] == 2
    assert audit["purged_rows_total"] == 8
    assert partitions["train"]["Ltime"].max() < partitions["validation"]["Stime"].min()
    assert partitions["validation"]["Ltime"].max() < partitions["test"]["Stime"].min()


def test_window_integrity_has_no_record_overlap_or_session_crossing() -> None:
    sorted_df = stable_temporal_sort(assign_record_ids(_synthetic_sessions()))
    session_df, _ = identify_natural_sessions(sorted_df, gap_seconds=3_600)
    partitions, _ = assign_splits_and_purge(session_df, window_size=3)

    integrity = window_integrity_summary(partitions, window_size=3)

    assert integrity["all_partition_record_ids_disjoint"] is True
    assert integrity["windows_can_cross_session"] is False
    assert integrity["record_id_overlaps"] == {
        "train_validation": 0,
        "train_test": 0,
        "validation_test": 0,
    }
    assert integrity["partitions"]["train"]["windows_created_separately_by_session"] == 8
    assert integrity["partitions"]["validation"]["windows_created_separately_by_session"] == 6
    assert integrity["partitions"]["test"]["windows_created_separately_by_session"] == 8


def test_materialization_writes_three_partitions_and_preserves_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cleaned_temporal.parquet"
    output_dir = tmp_path / "partitions"
    report = tmp_path / "reports" / "split_audit.json"
    _synthetic_sessions().to_parquet(source, index=False)
    source_hash_before = _sha256(source)

    payload = materialize_detection_temporal_split(
        input_path=source,
        output_dir=output_dir,
        report_path=report,
        session_gap_seconds=3_600,
        window_size=3,
    )

    assert _sha256(source) == source_hash_before
    assert report.exists()
    assert payload["acceptance"]["source_unchanged"] is True
    assert payload["acceptance"]["record_ids_disjoint"] is True
    for split in ("train", "validation", "test"):
        partition = pd.read_parquet(output_dir / f"{split}.parquet")
        assert not partition.empty
        assert set(partition["split"]) == {split}
        assert {"record_id", "temporal_session"}.issubset(partition.columns)


def test_materialization_refuses_to_overwrite_existing_partitions(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cleaned_temporal.parquet"
    output_dir = tmp_path / "partitions"
    report = tmp_path / "split_audit.json"
    _synthetic_sessions().to_parquet(source, index=False)
    materialize_detection_temporal_split(
        input_path=source,
        output_dir=output_dir,
        report_path=report,
        session_gap_seconds=3_600,
        window_size=3,
    )

    with pytest.raises(FileExistsError, match="não sobrescreve"):
        materialize_detection_temporal_split(
            input_path=source,
            output_dir=output_dir,
            report_path=report,
            session_gap_seconds=3_600,
            window_size=3,
        )


def test_record_id_must_not_exist_in_input() -> None:
    frame = _synthetic_sessions()
    frame["record_id"] = np.arange(len(frame))

    with pytest.raises(ValueError, match="já contém record_id"):
        assign_record_ids(frame)
