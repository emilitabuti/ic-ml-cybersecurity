"""Geração de tabelas comparativas e relatórios por tipo de ataque."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import config
from src.training.metrics import METRIC_NAMES, calculate_binary_metrics, format_mean_std

LOWER_IS_BETTER = {"fpr"}


def build_comparison_table(results_dir: str | Path | None = None) -> pd.DataFrame:
    """Monta tabela RF x DT x LSTM com média ± desvio padrão por métrica."""
    metrics_dir = Path(results_dir or config.TRAINING_REPORTS_DIR) / "metrics"
    rows: list[dict[str, object]] = []
    for result_path in sorted(metrics_dir.glob("*_metrics.json")):
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        row: dict[str, object] = {
            "model_type": payload["model_type"],
            "algorithm": payload["algorithm"],
        }
        for metric_name in METRIC_NAMES:
            row[metric_name] = format_mean_std(payload["summary"][metric_name])
            row[f"{metric_name}_mean"] = payload["summary"][metric_name]["mean"]
        rows.append(row)

    if not rows:
        raise FileNotFoundError(f"Nenhum resultado encontrado em {metrics_dir}")

    table = pd.DataFrame(rows)
    best_by_metric = _best_models_by_metric(table)
    table["best_metrics"] = table["model_type"].map(
        lambda model: ", ".join(
            metric for metric, best_model in best_by_metric.items() if best_model == model
        )
    )
    display_columns = ["model_type", "algorithm", *METRIC_NAMES, "best_metrics"]
    return table[display_columns]


def export_comparison_csv(
    output_path: str | Path,
    results_dir: str | Path | None = None,
) -> Path:
    """Exporta tabela comparativa em CSV compatível com LaTeX/Word."""
    table = build_comparison_table(results_dir=results_dir)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    return path


def build_attack_type_report(results_dir: str | Path | None = None) -> pd.DataFrame:
    """Calcula F1/Precision/Recall/FPR por tipo de ataque e modelo."""
    predictions_dir = Path(results_dir or config.TRAINING_REPORTS_DIR) / "predictions"
    frames = [
        pd.read_csv(path)
        for path in sorted(predictions_dir.glob("*_fold_predictions.csv"))
    ]
    if not frames:
        raise FileNotFoundError(f"Nenhuma predicao encontrada em {predictions_dir}")

    predictions = pd.concat(frames, ignore_index=True)
    attack_types = sorted(
        attack
        for attack in predictions["attack_type"].dropna().astype(str).unique()
        if attack.upper() not in {"BENIGN", "NORMAL"}
    )
    rows: list[dict[str, object]] = []
    for model_type, model_df in predictions.groupby("model_type"):
        for attack_type in attack_types:
            subset = model_df[
                (model_df["attack_type"].astype(str) == attack_type)
                | (model_df["y_true"].astype(int) == 0)
            ].copy()
            if subset.empty:
                continue
            y_true_attack = (subset["attack_type"].astype(str) == attack_type).astype(int)
            y_pred_attack = subset["y_pred"].astype(int)
            metrics = calculate_binary_metrics(
                y_true_attack,
                y_pred_attack,
                subset["y_score"].astype(float),
            )
            rows.append(
                {
                    "attack_type": attack_type,
                    "model_type": model_type,
                    "f1": metrics["f1"],
                    "precision": metrics["precision"],
                    "recall": metrics["recall"],
                    "fpr": metrics["fpr"],
                }
            )

    report = pd.DataFrame(rows)
    if report.empty:
        raise ValueError("Nao ha tipos de ataque maliciosos para relatorio.")
    return _annotate_attack_rank(report)


def export_attack_report_csv(
    output_path: str | Path,
    results_dir: str | Path | None = None,
) -> Path:
    """Exporta relatório por tipo de ataque em CSV."""
    report = build_attack_type_report(results_dir=results_dir)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(path, index=False)
    return path


def export_attack_report_markdown(
    output_path: str | Path,
    results_dir: str | Path | None = None,
) -> Path:
    """Exporta relatório por tipo de ataque em Markdown."""
    report = build_attack_type_report(results_dir=results_dir)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dataframe_to_markdown(report), encoding="utf-8")
    return path


def _best_models_by_metric(table: pd.DataFrame) -> dict[str, str]:
    best: dict[str, str] = {}
    for metric_name in METRIC_NAMES:
        values = table[f"{metric_name}_mean"].astype(float)
        index = values.idxmin() if metric_name in LOWER_IS_BETTER else values.idxmax()
        best[metric_name] = str(table.loc[index, "model_type"])
    return best


def _annotate_attack_rank(report: pd.DataFrame) -> pd.DataFrame:
    annotated = report.copy()
    annotated["detection_rank"] = ""
    for attack_type, group in annotated.groupby("attack_type"):
        best_index = group["f1"].idxmax()
        worst_index = group["f1"].idxmin()
        annotated.loc[best_index, "detection_rank"] = "best_by_f1"
        if worst_index != best_index:
            annotated.loc[worst_index, "detection_rank"] = "worst_by_f1"
    return annotated.sort_values(["attack_type", "model_type"]).reset_index(drop=True)


def _dataframe_to_markdown(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in frame.itertuples(index=False):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default=config.TRAINING_REPORTS_DIR)
    parser.add_argument("--comparison-csv", default="reports/comparison_metrics.csv")
    parser.add_argument("--attack-csv", default="reports/attack_type_metrics.csv")
    parser.add_argument("--attack-md", default=None)
    args = parser.parse_args()

    comparison_path = export_comparison_csv(
        output_path=args.comparison_csv,
        results_dir=args.results_dir,
    )
    attack_path = export_attack_report_csv(
        output_path=args.attack_csv,
        results_dir=args.results_dir,
    )
    print(f"Tabela comparativa exportada: {comparison_path}")
    print(f"Relatorio por tipo de ataque exportado: {attack_path}")
    if args.attack_md:
        markdown_path = export_attack_report_markdown(
            output_path=args.attack_md,
            results_dir=args.results_dir,
        )
        print(f"Relatorio Markdown exportado: {markdown_path}")


if __name__ == "__main__":
    main()
