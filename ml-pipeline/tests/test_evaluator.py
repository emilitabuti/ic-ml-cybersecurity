import json
from pathlib import Path

import pandas as pd

from src.training.evaluator import (
    build_attack_type_report,
    build_comparison_table,
    export_attack_report_markdown,
    export_attack_report_csv,
    export_comparison_csv,
)


def test_build_comparison_table_highlights_best_metrics(tmp_path: Path) -> None:
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    _write_metrics(metrics_dir / "random_forest_metrics.json", "random_forest", 0.9, 0.1)
    _write_metrics(metrics_dir / "decision_tree_metrics.json", "decision_tree", 0.7, 0.2)
    _write_metrics(metrics_dir / "lstm_metrics.json", "lstm", 0.8, 0.05)

    table = build_comparison_table(results_dir=tmp_path)

    rf_row = table.loc[table["model_type"] == "random_forest"].iloc[0]
    lstm_row = table.loc[table["model_type"] == "lstm"].iloc[0]
    assert "f1" in rf_row["best_metrics"]
    assert "fpr" in lstm_row["best_metrics"]


def test_export_comparison_csv_is_plain_csv(tmp_path: Path) -> None:
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    _write_metrics(metrics_dir / "random_forest_metrics.json", "random_forest", 0.9, 0.1)

    output = export_comparison_csv(tmp_path / "comparison.csv", results_dir=tmp_path)

    exported = pd.read_csv(output)
    assert exported.loc[0, "model_type"] == "random_forest"
    assert "f1" in exported.columns


def test_attack_type_report_identifies_best_and_worst_models(tmp_path: Path) -> None:
    predictions_dir = tmp_path / "predictions"
    predictions_dir.mkdir()
    rows = [
        {"model_type": "random_forest", "algorithm": "RF", "fold": 1, "sample_index": 0, "y_true": 0, "y_pred": 0, "y_score": 0.1, "attack_type": "BENIGN"},
        {"model_type": "random_forest", "algorithm": "RF", "fold": 1, "sample_index": 1, "y_true": 1, "y_pred": 1, "y_score": 0.9, "attack_type": "DDoS"},
        {"model_type": "decision_tree", "algorithm": "DT", "fold": 1, "sample_index": 0, "y_true": 0, "y_pred": 1, "y_score": 0.8, "attack_type": "BENIGN"},
        {"model_type": "decision_tree", "algorithm": "DT", "fold": 1, "sample_index": 1, "y_true": 1, "y_pred": 0, "y_score": 0.2, "attack_type": "DDoS"},
    ]
    pd.DataFrame(rows).to_csv(
        predictions_dir / "random_forest_fold_predictions.csv",
        index=False,
    )

    report = build_attack_type_report(results_dir=tmp_path)

    best = report.loc[report["detection_rank"] == "best_by_f1"].iloc[0]
    worst = report.loc[report["detection_rank"] == "worst_by_f1"].iloc[0]
    assert best["model_type"] == "random_forest"
    assert worst["model_type"] == "decision_tree"

    output = export_attack_report_csv(tmp_path / "attack.csv", results_dir=tmp_path)
    markdown_output = export_attack_report_markdown(
        tmp_path / "attack.md",
        results_dir=tmp_path,
    )
    assert output.exists()
    assert "| attack_type |" in markdown_output.read_text(encoding="utf-8")


def _write_metrics(path: Path, model_type: str, f1_mean: float, fpr_mean: float) -> None:
    payload = {
        "model_type": model_type,
        "algorithm": model_type,
        "summary": {
            "f1": {"mean": f1_mean, "std": 0.01},
            "auc_roc": {"mean": f1_mean, "std": 0.01},
            "precision": {"mean": f1_mean, "std": 0.01},
            "recall": {"mean": f1_mean, "std": 0.01},
            "fpr": {"mean": fpr_mean, "std": 0.01},
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
