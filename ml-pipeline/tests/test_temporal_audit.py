"""Testes da auditoria temporal para previsão prospectiva."""

from pathlib import Path

import pandas as pd
import pytest

from src.data.prospective.temporal_audit import (
    TemporalAuditError,
    audit_unsw_temporal_frame,
    audit_unsw_temporal_parquet,
)


def _valid_temporal_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Stime": [
                1_421_927_414,
                1_421_927_420,
                1_421_927_418,
                1_421_927_500,
            ],
            "Ltime": [
                1_421_927_415,
                1_421_927_425,
                1_421_927_419,
                1_421_927_501,
            ],
            "source_file": ["part-1", "part-1", "part-1", "part-2"],
            "Binary_Label": [0, 1, 0, 1],
            "attack_cat": ["BENIGN", "Exploits", "BENIGN", "DoS"],
        }
    )


def test_audit_accepts_unscaled_unix_seconds() -> None:
    report = audit_unsw_temporal_frame(_valid_temporal_frame())

    assert report["timestamp_contract"]["uses_unscaled_values"] is True
    assert report["rows"] == 4
    assert report["source_files"] == 2
    assert report["readiness"]["usable_for_temporal_pilot"] is True


def test_audit_reports_input_order_regression_per_file() -> None:
    report = audit_unsw_temporal_frame(_valid_temporal_frame())

    first_file = next(
        item for item in report["per_source_file"]
        if item["source_file"] == "part-1"
    )
    assert first_file["stime_monotonic_in_input_order"] is False
    assert first_file["stime_backward_transitions"] == 1
    assert report["ordering"]["input_order_is_globally_safe"] is False
    assert report["readiness"]["next_step"].startswith("Ordenar por")


def test_audit_advances_to_onset_identification_when_ordered() -> None:
    frame = _valid_temporal_frame().sort_values(
        ["source_file", "Stime"], kind="stable"
    )

    report = audit_unsw_temporal_frame(frame)

    assert report["ordering"]["input_order_is_globally_safe"] is True
    assert report["readiness"]["next_step"].startswith("Identificar transições")


def test_audit_rejects_scaled_timestamps() -> None:
    frame = _valid_temporal_frame()
    frame["Stime"] = [-0.2, -0.1, 0.0, 0.1]
    frame["Ltime"] = [-0.1, 0.0, 0.1, 0.2]

    with pytest.raises(TemporalAuditError, match="não escalados"):
        audit_unsw_temporal_frame(frame)


def test_audit_rejects_missing_temporal_column() -> None:
    frame = _valid_temporal_frame().drop(columns=["Stime"])

    with pytest.raises(TemporalAuditError, match="Stime"):
        audit_unsw_temporal_frame(frame)


def test_audit_reports_negative_duration_as_blocking() -> None:
    frame = _valid_temporal_frame()
    frame.loc[0, "Ltime"] = frame.loc[0, "Stime"] - 1

    report = audit_unsw_temporal_frame(frame)

    assert report["duration_seconds"]["negative_count"] == 1
    assert report["readiness"]["usable_for_temporal_pilot"] is False


def test_parquet_audit_persists_utf8_json(tmp_path: Path) -> None:
    source = tmp_path / "unsw_nb15_cleaned.parquet"
    output = tmp_path / "audit.json"
    _valid_temporal_frame().to_parquet(source, index=False)

    report = audit_unsw_temporal_parquet(source, output)

    assert output.exists()
    assert '"uses_unscaled_values": true' in output.read_text(encoding="utf-8")
    assert report["input"]["path"] == str(source)
