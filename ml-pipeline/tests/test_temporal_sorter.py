"""Testes da ordenação temporal não destrutiva."""

from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from src.data.prospective.temporal_sorter import sort_unsw_temporal_parquet


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feature": ["b-late", "a-tie-1", "a-early", "a-tie-2", "b-early"],
            "Stime": [
                1_421_927_520,
                1_421_927_420,
                1_421_927_410,
                1_421_927_420,
                1_421_927_500,
            ],
            "Ltime": [
                1_421_927_521,
                1_421_927_421,
                1_421_927_411,
                1_421_927_421,
                1_421_927_501,
            ],
            "source_file": ["part-b", "part-a", "part-a", "part-a", "part-b"],
            "Binary_Label": [1, 0, 0, 1, 0],
            "attack_cat": ["DoS", "BENIGN", "BENIGN", "Exploits", "BENIGN"],
        }
    )


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_sorter_creates_new_monotonic_parquet_and_preserves_input(tmp_path: Path) -> None:
    source = tmp_path / "cleaned.parquet"
    output = tmp_path / "sorted.parquet"
    report_path = tmp_path / "sort.json"
    _frame().to_parquet(source, index=False)
    source_hash = _hash(source)

    report = sort_unsw_temporal_parquet(source, output, report_path)

    result = pd.read_parquet(output)
    assert _hash(source) == source_hash
    assert result.groupby("source_file")["Stime"].apply(
        lambda values: values.is_monotonic_increasing
    ).all()
    assert report["validation"]["monotonic_within_source_file"] is True
    assert report["input"]["preserved"] is True
    assert report_path.exists()


def test_sorter_preserves_schema_rows_and_label_distribution(tmp_path: Path) -> None:
    source = tmp_path / "cleaned.parquet"
    output = tmp_path / "sorted.parquet"
    original = _frame()
    original.to_parquet(source, index=False)

    report = sort_unsw_temporal_parquet(source, output)
    result = pd.read_parquet(output)

    assert list(result.columns) == list(original.columns)
    assert result.dtypes.to_dict() == original.dtypes.to_dict()
    assert len(result) == len(original)
    assert result["Binary_Label"].value_counts().to_dict() == {
        0: 3,
        1: 2,
    }
    assert report["validation"]["row_count_preserved"] is True


def test_sorter_uses_original_order_as_stable_tie_breaker(tmp_path: Path) -> None:
    source = tmp_path / "cleaned.parquet"
    output = tmp_path / "sorted.parquet"
    _frame().to_parquet(source, index=False)

    sort_unsw_temporal_parquet(source, output)
    result = pd.read_parquet(output)

    tied = result[
        (result["source_file"] == "part-a")
        & (result["Stime"] == 1_421_927_420)
        & (result["Ltime"] == 1_421_927_421)
    ]
    assert tied["feature"].tolist() == ["a-tie-1", "a-tie-2"]


def test_sorter_refuses_to_overwrite_input(tmp_path: Path) -> None:
    source = tmp_path / "cleaned.parquet"
    _frame().to_parquet(source, index=False)

    with pytest.raises(ValueError, match="diferente"):
        sort_unsw_temporal_parquet(source, source)


def test_sorter_requires_explicit_overwrite_for_existing_output(
    tmp_path: Path,
) -> None:
    source = tmp_path / "cleaned.parquet"
    output = tmp_path / "sorted.parquet"
    _frame().to_parquet(source, index=False)
    _frame().to_parquet(output, index=False)

    with pytest.raises(FileExistsError, match="--overwrite"):
        sort_unsw_temporal_parquet(source, output)
