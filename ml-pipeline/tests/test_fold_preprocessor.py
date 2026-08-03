"""Testes do pré-processamento sem vazamento entre partições."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.features.fold_preprocessor import (
    FoldPreprocessor,
    materialize_train_validation_preprocessing,
)


def _frame(split: str, *, start_id: int = 0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "record_id": np.arange(start_id, start_id + 4),
            "srcip": ["10.0.0.1"] * 4,
            "dstip": ["10.0.0.2"] * 4,
            "sport": ["80", "0x0016", "-", "443"],
            "dsport": ["1000", "1001", "1002", "1003"],
            "proto": ["tcp", "tcp", "udp", "udp"],
            "state": ["FIN", "CON", "FIN", "CON"],
            "service": ["http", "-", "dns", "http"],
            "small": [1.0, 2.0, 3.0, 4.0],
            "large": [0.0, 2_000_000.0, 4_000_000.0, 8_000_000.0],
            "Stime": [100, 101, 102, 103],
            "Ltime": [100, 101, 102, 103],
            "source_file": ["capture"] * 4,
            "Binary_Label": [0, 1, 0, 1],
            "attack_cat": ["BENIGN", "DoS", "BENIGN", "Generic"],
            "temporal_session": [0] * 4,
            "split": [split] * 4,
        }
    )


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_fit_excludes_targets_identifiers_and_timestamps() -> None:
    preprocessor = FoldPreprocessor().fit(_frame("train"))

    names = preprocessor.get_feature_names_out()
    assert "sport" in names
    assert "Stime" not in names
    assert "Ltime" not in names
    assert "Binary_Label" not in names
    assert "record_id" not in names
    assert "srcip" not in names
    assert "dstip" not in names
    assert preprocessor.log1p_columns_ == ["large"]


def test_hexadecimal_ports_and_invalid_values_are_numeric() -> None:
    preprocessor = FoldPreprocessor().fit(_frame("train"))
    transformed = preprocessor.transform(_frame("train"))

    # 0x0016 equivale a 22; '-' é convertido para zero antes do scaler.
    expected = preprocessor.scaler_.transform(
        np.array([[22.0, 1001.0, 2.0, np.log1p(2_000_000.0)]])
    )[0, 0]
    assert transformed.loc[1, "sport"] == pytest.approx(expected)
    assert np.isfinite(transformed.to_numpy()).all()


def test_validation_cannot_change_log_columns_scaler_or_categories() -> None:
    train = _frame("train")
    validation = _frame("validation", start_id=10)
    validation["small"] = 1e15
    validation["proto"] = "unseen-protocol"
    preprocessor = FoldPreprocessor().fit(train)
    metadata_before = preprocessor.audit_metadata()

    transformed = preprocessor.transform(validation)
    metadata_after = preprocessor.audit_metadata()

    assert metadata_after == metadata_before
    assert "small" not in preprocessor.log1p_columns_
    assert not any("unseen-protocol" in name for name in transformed.columns)
    proto_columns = [name for name in transformed if name.startswith("proto_")]
    assert (transformed.loc[:, proto_columns].sum(axis=1) == 0).all()


def test_fit_rejects_non_train_refit_and_transform_before_fit() -> None:
    with pytest.raises(RuntimeError, match=r"fit\(\)"):
        FoldPreprocessor().transform(_frame("validation"))
    with pytest.raises(ValueError, match="exclusivamente"):
        FoldPreprocessor().fit(_frame("validation"))

    preprocessor = FoldPreprocessor().fit(_frame("train"))
    with pytest.raises(RuntimeError, match="refit"):
        preprocessor.fit(_frame("train"))


def test_save_and_load_preserve_transformation(tmp_path: Path) -> None:
    preprocessor = FoldPreprocessor().fit(_frame("train"))
    artifact = tmp_path / "preprocessor.joblib"
    expected = preprocessor.transform(_frame("validation", start_id=10))

    preprocessor.save(artifact)
    restored = FoldPreprocessor.load(artifact)

    pd.testing.assert_frame_equal(
        restored.transform(_frame("validation", start_id=10)), expected
    )


def test_materialization_writes_only_train_and_validation(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    artifact = tmp_path / "reports" / "preprocessor.joblib"
    report = tmp_path / "reports" / "audit.json"
    input_dir.mkdir()
    train_path = input_dir / "train.parquet"
    validation_path = input_dir / "validation.parquet"
    test_path = input_dir / "test.parquet"
    _frame("train").to_parquet(train_path, index=False)
    _frame("validation", start_id=10).to_parquet(validation_path, index=False)
    _frame("test", start_id=20).to_parquet(test_path, index=False)
    input_hashes = {_sha256(path) for path in (train_path, validation_path, test_path)}

    payload = materialize_train_validation_preprocessing(
        input_dir=input_dir,
        output_dir=output_dir,
        artifact_path=artifact,
        report_path=report,
        batch_size=2,
    )

    assert {_sha256(path) for path in (train_path, validation_path, test_path)} == input_hashes
    assert (output_dir / "train.parquet").exists()
    assert (output_dir / "validation.parquet").exists()
    assert not (output_dir / "test.parquet").exists()
    assert artifact.exists() and report.exists()
    assert all(payload["acceptance"].values())
    train_output = pd.read_parquet(output_dir / "train.parquet")
    validation_output = pd.read_parquet(output_dir / "validation.parquet")
    assert train_output.columns.tolist() == validation_output.columns.tolist()
    assert {"record_id", "Binary_Label", "Stime", "Ltime"}.issubset(train_output)


def test_materialization_refuses_overwrite(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    _frame("train").to_parquet(input_dir / "train.parquet", index=False)
    _frame("validation", start_id=10).to_parquet(
        input_dir / "validation.parquet", index=False
    )
    output_dir = tmp_path / "output"
    artifact = tmp_path / "preprocessor.joblib"
    report = tmp_path / "audit.json"
    materialize_train_validation_preprocessing(
        input_dir, output_dir, artifact, report
    )

    with pytest.raises(FileExistsError, match="não sobrescreve"):
        materialize_train_validation_preprocessing(
            input_dir, output_dir, artifact, report
        )
