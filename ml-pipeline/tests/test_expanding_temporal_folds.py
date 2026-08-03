"""Testes dos folds cronológicos expansivos com purga."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.expanding_temporal_folds import (
    create_expanding_fold_assignments,
    materialize_expanding_temporal_folds,
)


def _partition(split: str, *, start_id: int, start_time: int, rows: int) -> pd.DataFrame:
    label = np.arange(rows) % 2
    return pd.DataFrame(
        {
            "record_id": np.arange(start_id, start_id + rows),
            "Stime": np.arange(start_time, start_time + rows),
            "Ltime": np.arange(start_time, start_time + rows),
            "source_file": [f"{split}.parquet"] * rows,
            "Binary_Label": label,
            "attack_cat": np.where(label == 1, "DoS", "BENIGN"),
            "temporal_session": [0 if split == "train" else 1] * rows,
            "split": [split] * rows,
        }
    )


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_folds_are_expanding_chronological_purged_and_disjoint() -> None:
    train = _partition("train", start_id=0, start_time=100, rows=80)
    validation = _partition("validation", start_id=100, start_time=1_000, rows=20)

    folds, audit = create_expanding_fold_assignments(
        train, validation, n_folds=3, window_size=3
    )

    assert len(folds) == 3
    assert audit["purge_per_boundary_side_rows"] == 2
    assert audit["purged_rows_total"] == 12
    assert [fold["train"]["development_block"].nunique() for fold in folds] == [1, 2, 3]
    assert [fold["validation"]["development_block"].iloc[0] for fold in folds] == [1, 2, 3]
    assert len(folds[0]["train"]) < len(folds[1]["train"]) < len(folds[2]["train"])
    for fold in folds:
        assert fold["train"]["Ltime"].max() < fold["validation"]["Stime"].min()
        assert set(fold["train"]["record_id"]).isdisjoint(
            fold["validation"]["record_id"]
        )
        assert fold["train"]["Binary_Label"].nunique() == 2
        assert fold["validation"]["Binary_Label"].nunique() == 2


def test_materialization_creates_rows_and_windows_without_test(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "folds"
    report = tmp_path / "reports" / "folds.json"
    input_dir.mkdir()
    train_path = input_dir / "train.parquet"
    validation_path = input_dir / "validation.parquet"
    test_path = input_dir / "test.parquet"
    _partition("train", start_id=0, start_time=100, rows=80).to_parquet(
        train_path, index=False
    )
    _partition("validation", start_id=100, start_time=1_000, rows=20).to_parquet(
        validation_path, index=False
    )
    _partition("test", start_id=200, start_time=2_000, rows=20).to_parquet(
        test_path, index=False
    )
    hashes_before = [_sha256(path) for path in (train_path, validation_path, test_path)]

    payload = materialize_expanding_temporal_folds(
        input_dir=input_dir,
        output_dir=output_dir,
        report_path=report,
        n_folds=3,
        window_size=3,
    )

    assert [_sha256(path) for path in (train_path, validation_path, test_path)] == hashes_before
    assert all(payload["acceptance"].values())
    assert len(payload["folds"]) == 3
    assert report.exists()
    assert not (output_dir / "test.parquet").exists()
    for fold_number in range(1, 4):
        fold_dir = output_dir / f"fold_{fold_number}"
        assert (fold_dir / "train_rows.parquet").exists()
        assert (fold_dir / "validation_rows.parquet").exists()
        assert (fold_dir / "train_window_index.parquet").exists()
        assert (fold_dir / "validation_window_index.parquet").exists()
        train_windows = pd.read_parquet(fold_dir / "train_window_index.parquet")
        validation_windows = pd.read_parquet(
            fold_dir / "validation_window_index.parquet"
        )
        assert set(train_windows["development_block"]) == set(range(fold_number))
        assert set(validation_windows["development_block"]) == {fold_number}


def test_materialization_refuses_overwrite(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    _partition("train", start_id=0, start_time=100, rows=80).to_parquet(
        input_dir / "train.parquet", index=False
    )
    _partition("validation", start_id=100, start_time=1_000, rows=20).to_parquet(
        input_dir / "validation.parquet", index=False
    )
    output_dir = tmp_path / "folds"
    report = tmp_path / "folds.json"
    materialize_expanding_temporal_folds(
        input_dir, output_dir, report, n_folds=3, window_size=3
    )

    with pytest.raises(FileExistsError, match="não sobrescreve"):
        materialize_expanding_temporal_folds(
            input_dir, output_dir, report, n_folds=3, window_size=3
        )
