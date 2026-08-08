"""Testes da integração da seleção ao pipeline temporal."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.features.partition_window_builder import (
    materialize_train_validation_window_manifests,
)
from src.training.temporal_feature_selection import (
    materialize_temporal_feature_selection,
)


def _partition(split: str, *, start_id: int, validation_shift: float = 0.0) -> pd.DataFrame:
    rng = np.random.default_rng(42 + start_id)
    rows = 40
    signal = rng.normal(size=rows) + validation_shift
    label = (signal > validation_shift).astype(np.int8)
    return pd.DataFrame(
        {
            "record_id": np.arange(start_id, start_id + rows),
            "temporal_session": [0 if split == "train" else 1] * rows,
            "split": [split] * rows,
            "Binary_Label": label,
            "attack_cat": np.where(label == 1, "DoS", "BENIGN"),
            "source_file": [f"{split}.parquet"] * rows,
            "Stime": np.arange(100 + start_id, 100 + start_id + rows),
            "Ltime": np.arange(100 + start_id, 100 + start_id + rows),
            "signal": signal.astype(np.float32),
            "noise_a": rng.normal(size=rows).astype(np.float32),
            "noise_b": rng.normal(size=rows).astype(np.float32),
            "noise_c": rng.normal(size=rows).astype(np.float32),
        }
    )


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    input_dir = tmp_path / "preprocessed"
    manifest_dir = tmp_path / "windows"
    output_root = tmp_path / "selected"
    report_root = tmp_path / "reports"
    input_dir.mkdir()
    _partition("train", start_id=0).to_parquet(
        input_dir / "train.parquet", index=False
    )
    _partition("validation", start_id=100, validation_shift=1_000_000).to_parquet(
        input_dir / "validation.parquet", index=False
    )
    _partition("test", start_id=200).to_parquet(
        input_dir / "test.parquet", index=False
    )
    materialize_train_validation_window_manifests(
        input_dir=input_dir,
        output_dir=manifest_dir,
        report_path=tmp_path / "window_audit.json",
        window_size=5,
    )
    return input_dir, manifest_dir, output_root, report_root


def test_selection_is_fit_on_train_and_applied_before_windows(tmp_path: Path) -> None:
    input_dir, manifest_dir, output_root, report_root = _paths(tmp_path)
    inputs = [
        input_dir / "train.parquet",
        input_dir / "validation.parquet",
        input_dir / "test.parquet",
    ]
    hashes_before = [_sha256(path) for path in inputs]

    payload = materialize_temporal_feature_selection(
        input_dir=input_dir,
        window_manifest_dir=manifest_dir,
        output_root=output_root,
        report_root=report_root,
        top_n=2,
        n_estimators=10,
        window_size=5,
        window_batch_size=7,
    )

    assert [_sha256(path) for path in inputs] == hashes_before
    assert all(payload["acceptance"].values())
    assert payload["selection"]["fit_partition"] == "train"
    assert payload["selection"]["fit_rows"] == 40
    assert payload["selection"]["selected_feature_count"] == 2
    assert payload["selection"]["selected_feature_names"][0] == "signal"
    assert payload["outputs"]["train"]["window_realization"]["matches_manifest"]
    assert payload["outputs"]["validation"]["window_realization"][
        "matches_manifest"
    ]

    selected_dir = output_root / "top_2"
    train = pd.read_parquet(selected_dir / "train.parquet")
    validation = pd.read_parquet(selected_dir / "validation.parquet")
    assert train.columns.tolist() == validation.columns.tolist()
    assert len(train.columns) == 8 + 2
    assert not (selected_dir / "test.parquet").exists()
    assert (report_root / "top_2" / "feature_selection.json").exists()
    assert (report_root / "top_2" / "selection_audit.json").exists()


def test_selection_materialization_refuses_overwrite(tmp_path: Path) -> None:
    input_dir, manifest_dir, output_root, report_root = _paths(tmp_path)
    kwargs = {
        "input_dir": input_dir,
        "window_manifest_dir": manifest_dir,
        "output_root": output_root,
        "report_root": report_root,
        "top_n": 2,
        "n_estimators": 3,
        "window_size": 5,
    }
    materialize_temporal_feature_selection(**kwargs)

    with pytest.raises(FileExistsError, match="não sobrescreve"):
        materialize_temporal_feature_selection(**kwargs)
