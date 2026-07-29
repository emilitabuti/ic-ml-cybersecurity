"""Avalia o cenario simulado de SYN flood e exporta eventos para o dashboard."""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ML_PIPELINE_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_SCENARIO_DIR = ML_PIPELINE_ROOT / "reports" / "isabela" / "syn_flood"
DEFAULT_INPUT = DEFAULT_SCENARIO_DIR / "sandbox_tabular_dataset" / "syn_flood_synthetic_samples.csv"
DEFAULT_RESULTS_DIR = DEFAULT_SCENARIO_DIR
MODEL_NAME = "isabela-syn-flood-heuristic-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pontua amostras sinteticas e calcula metricas do cenario SYN flood."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="CSV gerado por generate_syn_flood_dataset.py.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Diretorio para CSV/JSON de resultados. Padrao: reports/isabela/syn_flood.",
    )
    return parser.parse_args()


def as_float(sample: dict[str, str], key: str) -> float:
    try:
        return float(sample[key])
    except KeyError as exc:
        raise KeyError(f"Coluna obrigatoria ausente: {key}") from exc
    except ValueError as exc:
        raise ValueError(f"Valor numerico invalido em {key}: {sample[key]!r}") from exc


def severity_from_prediction(prediction: str, confidence: float) -> str:
    if prediction.lower().startswith("normal"):
        return "safe"
    if confidence >= 0.90:
        return "critical"
    if confidence >= 0.70:
        return "warning"
    return "safe"


def score_sample(sample: dict[str, str]) -> tuple[str, float, list[str]]:
    syn_flag_count = as_float(sample, "syn_flag_count")
    ack_flag_count = as_float(sample, "ack_flag_count")
    flow_packets_s = as_float(sample, "flow_packets_s")
    flow_duration_ms = as_float(sample, "flow_duration_ms")
    same_srv_rate = as_float(sample, "same_srv_rate")
    total_fwd_packets = as_float(sample, "total_fwd_packets")
    total_bwd_packets = as_float(sample, "total_bwd_packets")

    syn_ack_ratio = syn_flag_count / max(ack_flag_count, 1.0)
    fwd_bwd_ratio = total_fwd_packets / max(total_bwd_packets, 1.0)

    triggered: list[str] = []
    if syn_ack_ratio >= 4.0:
        triggered.append("syn_ack_ratio")
    if flow_packets_s >= 140.0:
        triggered.append("high_packet_rate")
    if flow_duration_ms <= 5_000.0:
        triggered.append("short_duration_burst")
    if same_srv_rate >= 0.82:
        triggered.append("single_service_focus")
    if fwd_bwd_ratio >= 3.0:
        triggered.append("forward_backward_imbalance")

    confidence = round(min(0.99, 0.50 + len(triggered) * 0.09), 2)

    if len(triggered) >= 5 or confidence >= 0.95:
        prediction = "SYN Flood - High Intensity"
    elif len(triggered) == 4:
        prediction = "SYN Flood - Medium Intensity"
    elif len(triggered) == 3:
        prediction = "SYN Flood - Low Intensity"
    else:
        prediction = "Normal Traffic"
        confidence = round(max(0.30, 0.62 - len(triggered) * 0.08), 2)

    return prediction, confidence, triggered


def read_samples(input_path: Path) -> list[dict[str, str]]:
    with input_path.open("r", newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def evaluate(samples: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base_time = datetime.now(timezone.utc).replace(microsecond=0)
    rows: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    for offset, sample in enumerate(samples):
        started = time.perf_counter()
        prediction, confidence, triggered = score_sample(sample)
        elapsed_ms = (time.perf_counter() - started) * 1000

        expected_attack = int(sample["Binary_Label"]) == 1
        predicted_attack = not prediction.startswith("Normal")
        correct = expected_attack == predicted_attack
        severity = severity_from_prediction(prediction, confidence)
        timestamp = (base_time + timedelta(seconds=offset * 5)).isoformat().replace(
            "+00:00", "Z"
        )

        rows.append(
            {
                "sample_id": sample["sample_id"],
                "traffic_group": sample["traffic_group"],
                "expected_attack": expected_attack,
                "predicted_attack": predicted_attack,
                "expected_prediction": sample["expected_prediction"],
                "prediction": prediction,
                "confidence": confidence,
                "severity": severity,
                "correct": correct,
                "response_time_ms": round(elapsed_ms, 4),
                "triggered_signals": "|".join(triggered),
            }
        )
        events.append(
            {
                "prediction": prediction,
                "confidence": confidence,
                "model": MODEL_NAME,
                "timestamp": timestamp,
            }
        )

    return rows, events


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    correct = sum(1 for row in results if row["correct"])
    true_positive = sum(
        1 for row in results if row["expected_attack"] and row["predicted_attack"]
    )
    true_negative = sum(
        1 for row in results if not row["expected_attack"] and not row["predicted_attack"]
    )
    false_positive = sum(
        1 for row in results if not row["expected_attack"] and row["predicted_attack"]
    )
    false_negative = sum(
        1 for row in results if row["expected_attack"] and not row["predicted_attack"]
    )

    by_group: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[row["traffic_group"]].append(row)

    for group, rows in sorted(grouped.items()):
        severity_counts = Counter(row["severity"] for row in rows)
        by_group[group] = {
            "samples": len(rows),
            "correct": sum(1 for row in rows if row["correct"]),
            "average_confidence": round(
                sum(float(row["confidence"]) for row in rows) / len(rows), 4
            ),
            "average_response_time_ms": round(
                sum(float(row["response_time_ms"]) for row in rows) / len(rows), 4
            ),
            "severity_counts": dict(sorted(severity_counts.items())),
        }

    return {
        "scenario": "simulated_syn_flood_tabular_data",
        "model": MODEL_NAME,
        "total_samples": total,
        "correctly_identified": correct,
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "average_response_time_ms": round(
            sum(float(row["response_time_ms"]) for row in results) / total, 4
        )
        if total
        else 0.0,
        "by_group": by_group,
        "note": (
            "A classificacao usa heuristica temporaria. Estes resultados avaliam "
            "o fluxo simulado ate o dashboard, nao desempenho de um modelo ML real."
        ),
    }


def write_results(results_dir: Path, results: list[dict[str, Any]], events: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)

    results_csv = results_dir / "evaluation_results.csv"
    with results_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    (results_dir / "dashboard_history_events.json").write_text(
        json.dumps(events, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (results_dir / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    results_dir = args.results_dir.resolve()

    samples = read_samples(input_path)
    if not samples:
        raise ValueError(f"Nenhuma amostra encontrada em {input_path}")

    results, events = evaluate(samples)
    summary = summarize(results)
    write_results(results_dir, results, events, summary)

    print(f"Amostras analisadas: {summary['total_samples']}")
    print(f"Corretamente identificadas: {summary['correctly_identified']}")
    print(f"Falsos positivos: {summary['false_positive']}")
    print(f"Falsos negativos: {summary['false_negative']}")
    print(f"Acuracia simulada: {summary['accuracy']:.2%}")
    print(f"Eventos para dashboard: {results_dir / 'dashboard_history_events.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
