from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


PROTOCOL_PATH = Path("reports_temporal/unsw/protocol.json")


def test_protocol_freezes_development_winners_without_test_metrics() -> None:
    protocol = _load(PROTOCOL_PATH)
    summary = _load(
        Path("reports_temporal/unsw/development_experiments/development_summary.json")
    )

    assert protocol["status"] == "frozen_before_closed_test"
    assert summary["test_used"] is False
    assert protocol["test_policy"]["test_access_at_freeze"] is False
    assert protocol["test_policy"]["test_metrics_consulted_at_freeze"] is False
    assert protocol["temporal_protocol"]["partitions"]["test"]["status_at_freeze"] == "closed"

    expected: dict[str, str] = {}
    for algorithm in ("decision_tree", "random_forest", "lstm"):
        candidates = [row for row in summary["rows"] if row["algorithm"] == algorithm]
        winner = sorted(
            candidates,
            key=lambda row: (
                -row["f1_mean"],
                row["fpr_mean"],
                row["feature_count"]
                if row["feature_count"] is not None
                else row["feature_count_max"],
            ),
        )[0]
        expected[algorithm] = winner["variant"]

    frozen = {
        algorithm: configuration["variant"]
        for algorithm, configuration in protocol[
            "selected_configuration_by_algorithm"
        ].items()
    }
    assert frozen == expected == {
        "decision_tree": "top_10",
        "random_forest": "top_30",
        "lstm": "top_20",
    }
    assert protocol["overall_selected_configuration"] == {
        "algorithm": "random_forest",
        "variant": "top_30",
        "top_n": 30,
        "reason": "Maior F1 médio entre todas as configurações de desenvolvimento.",
    }


def test_protocol_evidence_and_source_hashes_are_current() -> None:
    protocol = _load(PROTOCOL_PATH)
    checked = 0
    for evidence in protocol["evidence"].values():
        if evidence["path"].endswith(".parquet"):
            continue
        assert _file_sha256(Path(evidence["path"])) == evidence["sha256"]
        checked += 1
    for path, expected in protocol["source_code"]["file_sha256"].items():
        assert _file_sha256(Path(path)) == expected
        checked += 1
    assert checked == 11


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
