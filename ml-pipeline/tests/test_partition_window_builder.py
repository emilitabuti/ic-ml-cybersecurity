"""Testes das janelas isoladas por partição e sessão."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.features.partition_window_builder import (
    create_partition_window_manifest,
    iter_partition_window_batches,
    materialize_train_validation_window_manifests,
)


def _partition(split: str, *, start_id: int = 0) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for session_id, count in ((0, 6), (1, 5)):
        start_time = 100 + session_id * 1_000
        for offset in range(count):
            label = offset % 2
            rows.append(
                {
                    "record_id": start_id + len(rows),
                    "temporal_session": session_id,
                    "split": split,
                    "Binary_Label": label,
                    "attack_cat": "DoS" if label else "BENIGN",
                    "source_file": f"capture-{session_id}",
                    "Stime": start_time + offset,
                    "Ltime": start_time + offset,
                    "feature_a": float(offset),
                    "feature_b": float(session_id),
                }
            )
    return pd.DataFrame(rows)


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_manifest_never_crosses_sessions_and_propagates_record_ids() -> None:
    frame = _partition("train")
    manifest, blocks = create_partition_window_manifest(
        frame, window_size=3, expected_split="train"
    )

    assert len(manifest) == (6 - 3 + 1) + (5 - 3 + 1)
    assert blocks == [
        {
            "temporal_block": 0,
            "temporal_session": 0,
            "source_file": "capture-0",
            "rows": 6,
            "windows": 4,
        },
        {
            "temporal_block": 1,
            "temporal_session": 1,
            "source_file": "capture-1",
            "rows": 5,
            "windows": 3,
        },
    ]
    record_columns = ["record_id_t00", "record_id_t01", "record_id_t02"]
    for _, window in manifest.iterrows():
        ids = window[record_columns].to_numpy(dtype=int)
        source_sessions = frame.set_index("record_id").loc[ids, "temporal_session"]
        assert source_sessions.nunique() == 1
        assert window["target_record_id"] == ids[-1]


def test_target_and_time_come_from_window_endpoint() -> None:
    frame = _partition("validation", start_id=100)
    manifest, _ = create_partition_window_manifest(
        frame, window_size=3, expected_split="validation"
    )
    first = manifest.iloc[0]

    assert first["target_record_id"] == 102
    assert first["Binary_Label"] == frame.iloc[2]["Binary_Label"]
    assert first["attack_cat"] == frame.iloc[2]["attack_cat"]
    assert first["window_start_stime"] == frame.iloc[0]["Stime"]
    assert first["window_end_ltime"] == frame.iloc[2]["Ltime"]


def test_batch_iterator_builds_expected_3d_and_flat_shapes() -> None:
    frame = _partition("train")
    batches = list(
        iter_partition_window_batches(
            frame,
            ["feature_a", "feature_b"],
            window_size=3,
            batch_size=2,
            expected_split="train",
        )
    )

    assert sum(len(batch.y) for batch in batches) == 7
    assert all(batch.X.shape[1:] == (3, 2) for batch in batches)
    assert all(batch.flatten().shape[1] == 6 for batch in batches)
    assert all(
        np.all(batch.window_record_ids[:, -1] == batch.target_record_ids)
        for batch in batches
    )
    assert all(
        np.all(batch.temporal_sessions == batch.temporal_sessions[0])
        for batch in batches
    )
    assert all(
        np.all(batch.source_files == batch.source_files[0]) for batch in batches
    )


def test_windows_do_not_cross_interleaved_source_files() -> None:
    frame = _partition("validation")
    frame.loc[2, "source_file"] = "interleaved"

    manifest, blocks = create_partition_window_manifest(
        frame, window_size=3, expected_split="validation"
    )

    # A primeira sessão vira blocos de tamanhos 2, 1 e 3. Só o último gera janela.
    assert [item["rows"] for item in blocks[:3]] == [2, 1, 3]
    assert len(manifest) == 1 + (5 - 3 + 1)
    assert set(manifest["target_source_file"]) == {"capture-0", "capture-1"}


def test_explicit_temporal_block_is_a_window_boundary() -> None:
    frame = _partition("train")
    frame["development_block"] = [0, 0, 0, 1, 1, 1, 2, 2, 2, 2, 2]

    manifest, blocks = create_partition_window_manifest(
        frame,
        window_size=3,
        expected_split="train",
        boundary_columns=["development_block"],
    )

    assert [item["rows"] for item in blocks] == [3, 3, 5]
    assert len(manifest) == 1 + 1 + 3
    assert manifest["development_block"].tolist() == [0, 1, 2, 2, 2]


def test_noncontiguous_or_mixed_partition_is_rejected() -> None:
    noncontiguous = _partition("train").iloc[[0, 6, 1, 2, 3, 4, 5, 7, 8, 9, 10]]
    with pytest.raises(ValueError, match="bloco contíguo"):
        create_partition_window_manifest(noncontiguous, window_size=3)

    mixed = _partition("train")
    mixed.loc[mixed.index[-1], "split"] = "validation"
    with pytest.raises(ValueError, match="uma só partição"):
        create_partition_window_manifest(mixed, window_size=3)


def test_metadata_cannot_be_passed_as_feature() -> None:
    with pytest.raises(ValueError, match="Metadados"):
        list(
            iter_partition_window_batches(
                _partition("train"),
                ["feature_a", "Stime"],
                window_size=3,
            )
        )


def test_materialization_writes_only_development_manifests(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    report = tmp_path / "reports" / "window_audit.json"
    input_dir.mkdir()
    train_path = input_dir / "train.parquet"
    validation_path = input_dir / "validation.parquet"
    test_path = input_dir / "test.parquet"
    _partition("train").to_parquet(train_path, index=False)
    _partition("validation", start_id=100).to_parquet(validation_path, index=False)
    _partition("test", start_id=200).to_parquet(test_path, index=False)
    hashes_before = [_sha256(path) for path in (train_path, validation_path, test_path)]

    payload = materialize_train_validation_window_manifests(
        input_dir=input_dir,
        output_dir=output_dir,
        report_path=report,
        window_size=3,
    )

    assert [_sha256(path) for path in (train_path, validation_path, test_path)] == hashes_before
    assert (output_dir / "train_window_index.parquet").exists()
    assert (output_dir / "validation_window_index.parquet").exists()
    assert not (output_dir / "test_window_index.parquet").exists()
    assert report.exists()
    assert all(payload["acceptance"].values())
    assert payload["outputs"]["train"]["windows"] == 7
    assert payload["cross_partition_integrity"][
        "train_validation_shared_record_ids"
    ] == 0


def test_materialization_rejects_record_overlap(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    _partition("train").to_parquet(input_dir / "train.parquet", index=False)
    _partition("validation").to_parquet(
        input_dir / "validation.parquet", index=False
    )

    with pytest.raises(ValueError, match="compartilham"):
        materialize_train_validation_window_manifests(
            input_dir=input_dir,
            output_dir=tmp_path / "output",
            report_path=tmp_path / "audit.json",
            window_size=3,
        )


def test_materialization_refuses_overwrite(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    _partition("train").to_parquet(input_dir / "train.parquet", index=False)
    _partition("validation", start_id=100).to_parquet(
        input_dir / "validation.parquet", index=False
    )
    output_dir = tmp_path / "output"
    report = tmp_path / "audit.json"
    materialize_train_validation_window_manifests(
        input_dir, output_dir, report, window_size=3
    )

    with pytest.raises(FileExistsError, match="não sobrescreve"):
        materialize_train_validation_window_manifests(
            input_dir, output_dir, report, window_size=3
        )
