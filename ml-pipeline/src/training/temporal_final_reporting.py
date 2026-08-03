"""Gera tabelas finais somente a partir de artefatos já avaliados."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_ROOT = Path("reports_temporal/unsw")


def generate_final_tables(root: str | Path = DEFAULT_ROOT) -> dict[str, Any]:
    report_root = Path(root)
    final = _load_json(report_root / "final_test_metrics.json")
    development = _load_json(
        report_root / "development_experiments/development_summary.json"
    )
    protocol = _load_json(report_root / "protocol.json")
    selector = _load_json(
        report_root / "final_evaluation/feature_ranking_train_validation.json"
    )
    output = report_root / "tables"
    output.mkdir(parents=True, exist_ok=True)

    metric_rows: list[dict[str, Any]] = []
    confusion_rows: list[dict[str, Any]] = []
    attack_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    for algorithm, result in final["results"].items():
        metric_rows.append(
            {
                "dataset": "UNSW-NB15",
                "protocol": "natural_session_chronological_holdout",
                "model": algorithm,
                "variant": result["variant"],
                "features": result["feature_count"],
                **result["metrics"],
                "fit_seconds": result["fit_seconds"],
                "inference_seconds": result["inference_seconds"],
                "artifact_size_bytes": result["artifact_size_bytes"],
                "test_windows": result["test_windows"],
                "test_start_stime": protocol["temporal_protocol"]["partitions"]["test"]["start_stime"],
                "test_end_ltime": protocol["temporal_protocol"]["partitions"]["test"]["end_ltime"],
            }
        )
        confusion_rows.append({"model": algorithm, **result["confusion_matrix"]})
        for attack_type, attack_result in result["metrics_by_attack_type"].items():
            attack_rows.append(
                {
                    "model": algorithm,
                    "attack_type": attack_type,
                    "positive_examples": attack_result["positive_examples"],
                    **attack_result["metrics"],
                }
            )
        dev = next(
            row
            for row in development["rows"]
            if row["algorithm"] == algorithm and row["variant"] == result["variant"]
        )
        comparison_rows.append(
            {
                "model": algorithm,
                "variant": result["variant"],
                "development_f1_mean": dev["f1_mean"],
                "test_f1": result["metrics"]["f1"],
                "test_minus_development_f1": result["metrics"]["f1"] - dev["f1_mean"],
                "development_pr_auc_mean": dev["pr_auc_mean"],
                "test_pr_auc": result["metrics"]["pr_auc"],
                "development_fpr_mean": dev["fpr_mean"],
                "test_fpr": result["metrics"]["fpr"],
            }
        )

    selected_names = selector["selected_feature_names"]
    importances = selector["feature_importances"]
    feature_names = selector["feature_names"]
    feature_rows = []
    for rank, name in enumerate(selected_names, start=1):
        feature_rows.append(
            {
                "rank": rank,
                "feature": name,
                "importance": importances[feature_names.index(name)],
                "used_by_decision_tree": rank <= 10,
                "used_by_lstm": rank <= 20,
                "used_by_random_forest": rank <= 30,
            }
        )

    tables = {
        "final_model_metrics": pd.DataFrame(metric_rows),
        "confusion_matrices": pd.DataFrame(confusion_rows),
        "attack_type_metrics": pd.DataFrame(attack_rows),
        "development_vs_test": pd.DataFrame(comparison_rows),
        "selected_features_final": pd.DataFrame(feature_rows),
    }
    artifacts: dict[str, Any] = {}
    for name, table in tables.items():
        csv_path = output / f"{name}.csv"
        table.to_csv(csv_path, index=False)
        artifacts[csv_path.name] = {
            "rows": len(table),
            "sha256": sha256(csv_path.read_bytes()).hexdigest(),
        }
    markdown_path = output / "final_model_metrics.md"
    markdown_path.write_text(_to_markdown(tables["final_model_metrics"]), encoding="utf-8")
    artifacts[markdown_path.name] = {
        "rows": len(tables["final_model_metrics"]),
        "sha256": sha256(markdown_path.read_bytes()).hexdigest(),
    }
    manifest = {
        "status": "final_tables_generated",
        "source_final_metrics_sha256": sha256(
            (report_root / "final_test_metrics.json").read_bytes()
        ).hexdigest(),
        "test_reopened": False,
        "artifacts": artifacts,
    }
    manifest_path = output / "tables_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def _to_markdown(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in frame.itertuples(index=False):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines) + "\n"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    print(json.dumps(generate_final_tables(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
