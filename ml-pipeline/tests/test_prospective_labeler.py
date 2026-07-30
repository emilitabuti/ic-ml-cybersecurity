"""Testes dos rótulos prospectivos."""

from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from src.features.prospective_labeler import (
    create_multi_horizon_labels,
    create_prospective_labels,
    generate_prospective_label_artifacts,
)
from src.data.prospective.temporal_audit import TemporalAuditError


BASE = 1_421_927_400


def _frame() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "source_file": [
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
                BASE,
                BASE + 4,
                BASE + 5,
                BASE + 5,
                BASE + 6,
                BASE + 7,
                BASE + 15,
                BASE,
                BASE + 3,
                BASE + 4,
            ],
            "Binary_Label": [0, 0, 0, 1, 1, 0, 1, 0, 0, 1],
        }
    )
    frame["Ltime"] = frame["Stime"]
    return frame


def _onsets() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": ["E-A1", "E-A2", "E-B1"],
            "source_file": ["part-a", "part-a", "part-b"],
            "onset_stime": [BASE + 5, BASE + 15, BASE + 4],
            "confirmed_onset": [True, True, True],
        }
    )


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_positive_interval_is_open_at_t_and_closed_at_horizon() -> None:
    labels = create_prospective_labels(
        _frame(),
        horizon_seconds=5,
        onsets=_onsets(),
    )
    part_a = labels.loc[labels["source_file"].eq("part-a")].set_index("Stime")

    assert part_a.loc[BASE, "Seconds_To_Attack"] == 5
    assert part_a.loc[BASE, "Future_Attack_Label"] == 1
    assert part_a.loc[BASE + 4, "Seconds_To_Attack"] == 1
    assert part_a.loc[BASE + 4, "Future_Attack_Label"] == 1
    assert part_a.loc[BASE + 7, "Seconds_To_Attack"] == 8
    assert part_a.loc[BASE + 7, "Future_Attack_Label"] == 0


def test_excludes_every_temporal_unit_with_active_attack() -> None:
    labels = create_prospective_labels(
        _frame(),
        horizon_seconds=5,
        onsets=_onsets(),
    )

    assert not labels["Current_Attack_Active"].any()
    part_a_times = set(labels.loc[labels["source_file"].eq("part-a"), "Stime"])
    assert BASE + 5 not in part_a_times
    assert BASE + 6 not in part_a_times
    assert BASE + 15 not in part_a_times


def test_never_crosses_source_file_boundary() -> None:
    frame = _frame().loc[_frame()["source_file"].eq("part-a")].copy()
    frame = pd.concat(
        [
            frame,
            pd.DataFrame(
                {
                    "source_file": ["part-empty"],
                    "Stime": [BASE + 14],
                    "Ltime": [BASE + 14],
                    "Binary_Label": [0],
                }
            ),
        ],
        ignore_index=True,
    )
    onsets = _onsets()
    labels = create_prospective_labels(
        frame,
        horizon_seconds=60,
        onsets=onsets.loc[onsets["source_file"].eq("part-a")],
    )
    empty = labels.loc[labels["source_file"].eq("part-empty")].iloc[0]

    assert pd.isna(empty["Seconds_To_Attack"])
    assert empty["Future_Attack_Label"] == 0
    assert empty["Next_Attack_Event_ID"] is None


def test_creates_independent_rows_for_each_horizon() -> None:
    labels = create_multi_horizon_labels(
        _frame(),
        horizons=[60, 5, 15, 30],
        onsets=_onsets(),
    )

    assert labels["Prediction_Horizon_Seconds"].unique().tolist() == [
        5,
        15,
        30,
        60,
    ]
    eligible_bins = labels[
        ["source_file", "Stime"]
    ].drop_duplicates()
    assert len(labels) == len(eligible_bins) * 4


def test_rejects_onset_without_attack_at_the_same_instant() -> None:
    invalid = _onsets().copy()
    invalid.loc[0, "onset_stime"] = BASE + 2

    with pytest.raises(TemporalAuditError, match="sem ataque"):
        create_prospective_labels(
            _frame(),
            horizon_seconds=5,
            onsets=invalid,
        )


def test_excludes_benign_start_covered_by_earlier_attack_interval() -> None:
    frame = _frame()
    attack = (
        frame["source_file"].eq("part-a")
        & frame["Stime"].eq(BASE + 5)
        & frame["Binary_Label"].eq(1)
    )
    frame.loc[attack, "Ltime"] = BASE + 7

    labels = create_prospective_labels(
        frame,
        horizon_seconds=5,
        onsets=_onsets(),
    )
    part_a_times = set(labels.loc[labels["source_file"].eq("part-a"), "Stime"])

    assert BASE + 7 not in part_a_times


def test_rejects_unsorted_group() -> None:
    frame = _frame()
    frame.loc[1, "Stime"] = BASE - 1

    with pytest.raises(TemporalAuditError, match="não estão ordenados"):
        create_prospective_labels(
            frame,
            horizon_seconds=5,
            onsets=_onsets(),
        )


def test_artifact_generation_preserves_inputs_and_writes_utf8(
    tmp_path: Path,
) -> None:
    source = tmp_path / "temporal.parquet"
    onset_source = tmp_path / "onsets.parquet"
    output = tmp_path / "labels.parquet"
    report = tmp_path / "labels.json"
    _frame().to_parquet(source, index=False)
    _onsets().to_parquet(onset_source, index=False)
    source_hash = _hash(source)
    onset_hash = _hash(onset_source)

    result = generate_prospective_label_artifacts(
        source,
        onset_source,
        output,
        report,
        horizons=[5, 15],
    )

    assert _hash(source) == source_hash
    assert _hash(onset_source) == onset_hash
    assert output.exists()
    assert result["validation"]["all_output_units_are_benign"] is True
    assert "Rótulos prospectivos" in report.read_text(encoding="utf-8")


def test_refuses_to_overwrite_output_implicitly(tmp_path: Path) -> None:
    source = tmp_path / "temporal.parquet"
    onset_source = tmp_path / "onsets.parquet"
    output = tmp_path / "labels.parquet"
    report = tmp_path / "labels.json"
    _frame().to_parquet(source, index=False)
    _onsets().to_parquet(onset_source, index=False)
    output.write_bytes(b"existing")

    with pytest.raises(FileExistsError, match="--overwrite"):
        generate_prospective_label_artifacts(
            source,
            onset_source,
            output,
            report,
        )
