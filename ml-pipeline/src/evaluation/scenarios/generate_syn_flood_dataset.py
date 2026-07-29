"""Gera dados tabulares sinteticos para um cenario simulado de SYN flood."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ML_PIPELINE_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_SCENARIO_DIR = ML_PIPELINE_ROOT / "reports" / "isabela" / "syn_flood"
DEFAULT_OUTPUT_DIR = DEFAULT_SCENARIO_DIR / "sandbox_tabular_dataset"
DEFAULT_OUTPUT_FILE = "syn_flood_synthetic_samples.csv"
DEFAULT_SEED = 42

FIELDNAMES = [
    "sample_id",
    "traffic_group",
    "expected_prediction",
    "expected_severity",
    "flow_duration_ms",
    "total_fwd_packets",
    "total_bwd_packets",
    "total_length_fwd_packets",
    "total_length_bwd_packets",
    "fwd_packet_length_max",
    "bwd_packet_length_max",
    "flow_bytes_s",
    "flow_packets_s",
    "syn_flag_count",
    "ack_flag_count",
    "rst_flag_count",
    "psh_flag_count",
    "unique_dst_ports",
    "same_srv_rate",
    "failed_login_attempts",
    "Binary_Label",
    "Attack_Type",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cria varias amostras sinteticas de trafego normal e SYN flood."
    )
    parser.add_argument(
        "--samples-per-group",
        type=int,
        default=30,
        help="Quantidade de amostras por grupo. Padrao: 30.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Diretorio de saida. Padrao: reports/isabela/syn_flood/sandbox_tabular_dataset.",
    )
    parser.add_argument(
        "--filename",
        default=DEFAULT_OUTPUT_FILE,
        help=f"Nome do CSV gerado. Padrao: {DEFAULT_OUTPUT_FILE}.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Semente para reprodutibilidade. Padrao: 42.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescreve o CSV se ele ja existir.",
    )
    return parser.parse_args()


def randint(rng: random.Random, low: int, high: int) -> int:
    return rng.randint(low, high)


def uniform(rng: random.Random, low: float, high: float, digits: int = 2) -> float:
    return round(rng.uniform(low, high), digits)


def packet_lengths(row: dict[str, object], rng: random.Random) -> None:
    fwd_packets = int(row["total_fwd_packets"])
    bwd_packets = int(row["total_bwd_packets"])
    fwd_max = int(row["fwd_packet_length_max"])
    bwd_max = int(row["bwd_packet_length_max"])
    duration_ms = max(float(row["flow_duration_ms"]), 1.0)

    avg_fwd = uniform(rng, fwd_max * 0.45, fwd_max * 0.75)
    avg_bwd = uniform(rng, bwd_max * 0.45, bwd_max * 0.75)
    total_fwd_length = int(fwd_packets * avg_fwd)
    total_bwd_length = int(bwd_packets * avg_bwd)

    row["total_length_fwd_packets"] = total_fwd_length
    row["total_length_bwd_packets"] = total_bwd_length
    row["flow_bytes_s"] = round((total_fwd_length + total_bwd_length) / (duration_ms / 1000), 2)
    row["flow_packets_s"] = round((fwd_packets + bwd_packets) / (duration_ms / 1000), 2)


def normal_sample(rng: random.Random, index: int) -> dict[str, object]:
    fwd = randint(rng, 25, 130)
    bwd = randint(rng, max(20, fwd - 35), fwd + 45)
    row: dict[str, object] = {
        "sample_id": f"normal-{index:03d}",
        "traffic_group": "normal",
        "expected_prediction": "Normal Traffic",
        "expected_severity": "safe",
        "flow_duration_ms": randint(rng, 8_000, 60_000),
        "total_fwd_packets": fwd,
        "total_bwd_packets": bwd,
        "fwd_packet_length_max": randint(rng, 300, 1200),
        "bwd_packet_length_max": randint(rng, 300, 1200),
        "syn_flag_count": randint(rng, 1, 12),
        "ack_flag_count": randint(rng, max(10, bwd - 15), bwd + 20),
        "rst_flag_count": randint(rng, 0, 2),
        "psh_flag_count": randint(rng, 2, 20),
        "unique_dst_ports": randint(rng, 3, 16),
        "same_srv_rate": uniform(rng, 0.20, 0.78),
        "failed_login_attempts": randint(rng, 0, 1),
        "Binary_Label": 0,
        "Attack_Type": "Normal Traffic",
    }
    packet_lengths(row, rng)
    return row


def syn_flood_sample(rng: random.Random, intensity: str, index: int) -> dict[str, object]:
    profiles = {
        "low": {
            "duration": (2_200, 5_000),
            "fwd": (260, 520),
            "bwd": (60, 170),
            "syn": (180, 420),
            "ack": (45, 140),
            "same_srv": (0.82, 0.93),
            "expected_severity": "warning",
        },
        "medium": {
            "duration": (1_000, 2_400),
            "fwd": (700, 1_300),
            "bwd": (30, 95),
            "syn": (620, 1_160),
            "ack": (24, 85),
            "same_srv": (0.90, 0.98),
            "expected_severity": "critical",
        },
        "high": {
            "duration": (450, 1_200),
            "fwd": (1_300, 2_400),
            "bwd": (8, 45),
            "syn": (1_180, 2_250),
            "ack": (6, 38),
            "same_srv": (0.96, 1.00),
            "expected_severity": "critical",
        },
    }
    profile = profiles[intensity]
    row = {
        "sample_id": f"syn-flood-{intensity}-{index:03d}",
        "traffic_group": f"syn_flood_{intensity}",
        "expected_prediction": f"SYN Flood - {intensity.title()} Intensity",
        "expected_severity": profile["expected_severity"],
        "flow_duration_ms": randint(rng, *profile["duration"]),
        "total_fwd_packets": randint(rng, *profile["fwd"]),
        "total_bwd_packets": randint(rng, *profile["bwd"]),
        "fwd_packet_length_max": randint(rng, 64, 180),
        "bwd_packet_length_max": randint(rng, 48, 160),
        "syn_flag_count": randint(rng, *profile["syn"]),
        "ack_flag_count": randint(rng, *profile["ack"]),
        "rst_flag_count": randint(rng, 0, 4),
        "psh_flag_count": randint(rng, 0, 6),
        "unique_dst_ports": randint(rng, 1, 2),
        "same_srv_rate": uniform(rng, *profile["same_srv"]),
        "failed_login_attempts": 0,
        "Binary_Label": 1,
        "Attack_Type": f"SYN Flood - {intensity.title()} Intensity",
    }
    packet_lengths(row, rng)
    return row


def build_dataset(samples_per_group: int, seed: int) -> list[dict[str, object]]:
    if samples_per_group <= 0:
        raise ValueError("--samples-per-group deve ser maior que zero.")

    rng = random.Random(seed)
    rows: list[dict[str, object]] = []

    for index in range(1, samples_per_group + 1):
        rows.append(normal_sample(rng, index))
        rows.append(syn_flood_sample(rng, "low", index))
        rows.append(syn_flood_sample(rng, "medium", index))
        rows.append(syn_flood_sample(rng, "high", index))

    return rows


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / args.filename

    if output_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Arquivo ja existe: {output_path}. Use --overwrite para recriar."
        )

    rows = build_dataset(args.samples_per_group, args.seed)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Dataset sintetico criado: {output_path}")
    print(f"Amostras geradas: {len(rows)}")
    print("Proximo passo: python -m src.evaluation.scenarios.evaluate_syn_flood_scenario")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
