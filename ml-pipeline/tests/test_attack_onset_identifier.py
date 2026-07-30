"""Testes da identificação de inícios de ataque."""

from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from src.data.prospective.attack_onset_identifier import (
    build_attack_event_catalog,
    identify_attack_onsets_parquet,
)
from src.data.prospective.temporal_audit import TemporalAuditError


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_file": [
                "part-a",
                "part-a",
                "part-a",
                "part-a",
                "part-a",
                "part-a",
                "part-a",
                "part-a",
                "part-b",
                "part-b",
                "part-b",
            ],
            "Stime": [
                1_421_927_400,
                1_421_927_401,
                1_421_927_401,
                1_421_927_401,
                1_421_927_401,
                1_421_927_402,
                1_421_927_403,
                1_421_927_404,
                1_421_927_400,
                1_421_927_401,
                1_421_927_402,
            ],
            "Ltime": [
                1_421_927_400,
                1_421_927_401,
                1_421_927_402,
                1_421_927_401,
                1_421_927_402,
                1_421_927_402,
                1_421_927_403,
                1_421_927_405,
                1_421_927_400,
                1_421_927_401,
                1_421_927_402,
            ],
            "Binary_Label": [0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1],
            "attack_cat": [
                "BENIGN",
                "BENIGN",
                "Exploits",
                "BENIGN",
                "Exploits",
                "Exploits",
                "BENIGN",
                "DoS",
                "Generic",
                "BENIGN",
                "Generic",
            ],
        }
    )


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_consolidates_tied_rows_before_identifying_onsets() -> None:
    catalog, diagnostics = build_attack_event_catalog(_frame())

    part_a = catalog.loc[catalog["source_file"].eq("part-a")]
    assert len(part_a) == 2
    assert part_a["confirmed_onset"].tolist() == [True, True]
    assert part_a["onset_stime"].tolist() == [
        1_421_927_401,
        1_421_927_404,
    ]
    assert diagnostics["raw_row_benign_to_attack_transitions"] == 4
    assert diagnostics["confirmed_timestamp_onsets"] == 3
    assert diagnostics["mixed_temporal_bins"] == 1


def test_marks_attack_at_file_boundary_without_claiming_confirmed_onset() -> None:
    catalog, diagnostics = build_attack_event_catalog(_frame())

    part_b = catalog.loc[catalog["source_file"].eq("part-b")]
    assert part_b["confirmed_onset"].tolist() == [False, True]
    assert part_b["transition_type"].tolist() == [
        "attack_at_file_boundary",
        "benign_to_attack",
    ]
    assert pd.isna(part_b.iloc[0]["previous_observed_stime"])
    assert diagnostics["attack_runs_at_file_boundary"] == 1


def test_attack_interval_prevents_false_repeated_onset() -> None:
    frame = pd.DataFrame(
        {
            "source_file": ["part-a"] * 4,
            "Stime": [
                1_421_927_399,
                1_421_927_400,
                1_421_927_401,
                1_421_927_402,
            ],
            "Ltime": [
                1_421_927_399,
                1_421_927_405,
                1_421_927_401,
                1_421_927_402,
            ],
            "Binary_Label": [0, 1, 0, 1],
            "attack_cat": ["BENIGN", "DoS", "BENIGN", "DoS"],
        }
    )

    catalog, diagnostics = build_attack_event_catalog(frame)

    assert len(catalog) == 1
    assert catalog.iloc[0]["onset_stime"] == 1_421_927_400
    assert catalog.iloc[0]["end_stime"] == 1_421_927_402
    assert diagnostics["active_attack_bins_without_attack_start"] == 1


def test_assigns_deterministic_categories_and_event_ids() -> None:
    catalog, _ = build_attack_event_catalog(_frame())

    assert catalog["event_id"].tolist() == [
        "UNSW-E000001",
        "UNSW-E000002",
        "UNSW-E000003",
        "UNSW-E000004",
    ]
    assert catalog.iloc[0]["primary_attack_category"] == "Exploits"
    assert catalog.iloc[0]["attack_categories"] == "Exploits"


def test_rejects_unsorted_source_file() -> None:
    frame = _frame()
    frame.loc[2, "Stime"] = 1_421_927_399

    with pytest.raises(TemporalAuditError, match="não está ordenado"):
        build_attack_event_catalog(frame)


def test_parquet_execution_is_non_destructive_and_persists_outputs(
    tmp_path: Path,
) -> None:
    source = tmp_path / "temporal.parquet"
    catalog_path = tmp_path / "onsets.parquet"
    report_path = tmp_path / "onsets.json"
    _frame().to_parquet(source, index=False)
    original_hash = _hash(source)

    report = identify_attack_onsets_parquet(
        source,
        catalog_path,
        report_path,
    )

    assert _hash(source) == original_hash
    assert catalog_path.exists()
    assert report_path.exists()
    assert report["input"]["preserved"] is True
    assert len(pd.read_parquet(catalog_path)) == 4
    assert "rótulos prospectivos" in report_path.read_text(encoding="utf-8")


def test_refuses_existing_output_without_explicit_overwrite(
    tmp_path: Path,
) -> None:
    source = tmp_path / "temporal.parquet"
    catalog_path = tmp_path / "onsets.parquet"
    report_path = tmp_path / "onsets.json"
    _frame().to_parquet(source, index=False)
    catalog_path.write_bytes(b"existing")

    with pytest.raises(FileExistsError, match="--overwrite"):
        identify_attack_onsets_parquet(
            source,
            catalog_path,
            report_path,
        )
