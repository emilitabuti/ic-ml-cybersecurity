"""Testes dos atributos históricos causais."""

from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from src.features.temporal_aggregator import (
    build_historical_features,
    generate_historical_feature_artifacts,
)


BASE = 1_421_927_400


def _flows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_file": ["part-a", "part-a", "part-a", "part-b"],
            "Stime": [BASE, BASE + 2, BASE + 8, BASE],
            "Ltime": [BASE + 1, BASE + 4, BASE + 20, BASE + 1],
            "dur": [1.0, 2.0, 12.0, 1.0],
            "sbytes": [100, 200, 9000, 50],
            "dbytes": [10, 20, 900, 5],
            "Spkts": [2, 4, 90, 1],
            "Dpkts": [1, 2, 9, 1],
            "srcip": ["a", "b", "future", "z"],
            "dstip": ["x", "y", "future", "x"],
            "sport": ["1", "2", "9", "1"],
            "dsport": ["80", "443", "9", "80"],
            "proto": ["tcp", "udp", "tcp", "tcp"],
            "state": ["FIN", "CON", "INT", "FIN"],
            "Binary_Label": [0, 0, 1, 0],
        }
    )


def _references() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_file": ["part-a", "part-b"],
            "Stime": [BASE + 5, BASE + 5],
        }
    )


def _labels() -> pd.DataFrame:
    rows = []
    for source_file in ("part-a", "part-b"):
        for horizon in (5, 15):
            rows.append(
                {
                    "source_file": source_file,
                    "Stime": BASE + 5,
                    "Prediction_Horizon_Seconds": horizon,
                    "Future_Attack_Label": int(source_file == "part-a"),
                    "Seconds_To_Attack": 5.0 if source_file == "part-a" else None,
                    "Current_Attack_Active": False,
                }
            )
    return pd.DataFrame(rows)


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_uses_only_flows_completed_at_or_before_t() -> None:
    features = build_historical_features(
        _flows(),
        _references(),
        lookbacks=[10],
    )
    part_a = features.loc[features["source_file"].eq("part-a")].iloc[0]

    assert part_a["completed_flows_10s"] == 2
    assert part_a["total_bytes_10s"] == 330
    assert part_a["total_packets_10s"] == 9
    assert part_a["distinct_dst_ips_10s"] == 2


def test_future_flow_mutation_cannot_change_features() -> None:
    flows = _flows()
    original = build_historical_features(flows, _references(), lookbacks=[10])
    flows.loc[flows["Ltime"].gt(BASE + 5), "sbytes"] = 999_999_999
    mutated = build_historical_features(flows, _references(), lookbacks=[10])

    pd.testing.assert_frame_equal(original, mutated)


def test_window_is_open_at_lower_and_closed_at_t() -> None:
    flows = _flows()
    extra = flows.iloc[[0]].copy()
    extra["Stime"] = BASE - 10
    extra["Ltime"] = BASE - 5
    flows = pd.concat([extra, flows], ignore_index=True)

    features = build_historical_features(
        flows,
        _references(),
        lookbacks=[10],
    )
    part_a = features.loc[features["source_file"].eq("part-a")].iloc[0]

    assert part_a["completed_flows_10s"] == 2


def test_never_crosses_source_file_boundary() -> None:
    features = build_historical_features(
        _flows(),
        _references(),
        lookbacks=[10],
    )
    part_b = features.loc[features["source_file"].eq("part-b")].iloc[0]

    assert part_b["completed_flows_10s"] == 1
    assert part_b["total_bytes_10s"] == 55


def test_output_contains_no_target_or_current_label() -> None:
    features = build_historical_features(
        _flows(),
        _references(),
        lookbacks=[10],
    )

    forbidden = {
        "Binary_Label",
        "Future_Attack_Label",
        "Seconds_To_Attack",
        "Next_Attack_Onset",
    }
    assert forbidden.isdisjoint(features.columns)


def test_artifact_generation_is_non_destructive(tmp_path: Path) -> None:
    source = tmp_path / "flows.parquet"
    labels = tmp_path / "labels.parquet"
    output = tmp_path / "features.parquet"
    report = tmp_path / "features.json"
    _flows().to_parquet(source, index=False)
    _labels().to_parquet(labels, index=False)
    source_hash = _hash(source)
    labels_hash = _hash(labels)

    result = generate_historical_feature_artifacts(
        source,
        labels,
        output,
        report,
        lookbacks=[10],
    )

    assert _hash(source) == source_hash
    assert _hash(labels) == labels_hash
    assert result["validation"]["target_columns_absent"] is True
    assert output.exists()
    assert "históricos" in report.read_text(encoding="utf-8")


def test_refuses_implicit_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "flows.parquet"
    labels = tmp_path / "labels.parquet"
    output = tmp_path / "features.parquet"
    report = tmp_path / "features.json"
    _flows().to_parquet(source, index=False)
    _labels().to_parquet(labels, index=False)
    output.write_bytes(b"existing")

    with pytest.raises(FileExistsError, match="--overwrite"):
        generate_historical_feature_artifacts(
            source,
            labels,
            output,
            report,
            lookbacks=[10],
        )
