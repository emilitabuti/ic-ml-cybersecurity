"""Atributos históricos causais para previsão antecipada.

Somente fluxos concluídos em ``(t - W, t]`` entram nos atributos. O instante
de conclusão, ``Ltime``, representa quando duração, bytes e pacotes ficam
disponíveis operacionalmente.

Uso:
    python -m src.features.temporal_aggregator
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
import tempfile
from typing import Any, Sequence

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import roc_auc_score

from src.data.prospective.temporal_audit import TemporalAuditError


DEFAULT_LOOKBACKS = (30, 60, 120)
FLOW_COLUMNS = (
    "source_file",
    "Stime",
    "Ltime",
    "dur",
    "sbytes",
    "dbytes",
    "Spkts",
    "Dpkts",
    "srcip",
    "dstip",
    "sport",
    "dsport",
    "proto",
    "state",
    "Binary_Label",
)
TARGET_COLUMNS = {
    "Binary_Label",
    "Future_Attack_Label",
    "Seconds_To_Attack",
    "Next_Attack_Onset",
    "Next_Attack_Event_ID",
    "Prediction_Horizon_Seconds",
}


def build_historical_features(
    flows: pd.DataFrame,
    reference_times: pd.DataFrame,
    *,
    lookbacks: Sequence[int] = DEFAULT_LOOKBACKS,
) -> pd.DataFrame:
    """Calcula atributos de fluxos já concluídos para cada instante."""
    windows = _normalize_lookbacks(lookbacks)
    _validate_frames(flows, reference_times)
    references = (
        reference_times[["source_file", "Stime"]]
        .drop_duplicates()
        .sort_values(["source_file", "Stime"], kind="stable")
        .reset_index(drop=True)
    )
    result_parts: list[pd.DataFrame] = []
    flow_groups = {
        str(key): group.sort_values(["Ltime", "Stime"], kind="stable")
        for key, group in flows.groupby(
            "source_file",
            sort=False,
            observed=True,
        )
    }
    for source_file, queries in references.groupby(
        "source_file",
        sort=True,
        observed=True,
    ):
        group = flow_groups.get(str(source_file))
        if group is None:
            raise TemporalAuditError(
                f"Não existem fluxos para source_file={source_file}."
            )
        part = queries.copy()
        _append_group_features(part, group, windows)
        result_parts.append(part)
    result = pd.concat(result_parts, ignore_index=True)
    forbidden = TARGET_COLUMNS.intersection(result.columns)
    if forbidden:
        raise RuntimeError(f"Atributos contêm alvos proibidos: {sorted(forbidden)}")
    return result


def generate_historical_feature_artifacts(
    input_path: str | Path,
    labels_path: str | Path,
    output_path: str | Path,
    report_path: str | Path,
    *,
    lookbacks: Sequence[int] = DEFAULT_LOOKBACKS,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Gera atributos e análise descritiva sem alterar as entradas."""
    source = Path(input_path)
    label_source = Path(labels_path)
    destination = Path(output_path)
    report_destination = Path(report_path)
    _validate_paths(
        (source, label_source),
        (destination, report_destination),
        overwrite=overwrite,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    report_destination.parent.mkdir(parents=True, exist_ok=True)
    windows = _normalize_lookbacks(lookbacks)
    started = perf_counter()
    hashes_before = {
        str(source): _file_sha256(source),
        str(label_source): _file_sha256(label_source),
    }

    available = set(pq.read_schema(source).names)
    missing = sorted(set(FLOW_COLUMNS) - available)
    if missing:
        raise TemporalAuditError(f"Colunas obrigatórias ausentes: {missing}")
    flows = pd.read_parquet(source, columns=list(FLOW_COLUMNS))
    labels = pd.read_parquet(label_source)
    references = labels[["source_file", "Stime"]].drop_duplicates()
    features = build_historical_features(
        flows,
        references,
        lookbacks=windows,
    )
    analysis = _analyze_precursor_signals(
        features,
        labels,
        flows,
        lookbacks=windows,
    )

    temporary_output = _temporary_path(destination, ".tmp.parquet")
    temporary_report = _temporary_path(report_destination, ".tmp.json")
    try:
        features.to_parquet(
            temporary_output,
            index=False,
            compression="zstd",
        )
        written = pd.read_parquet(temporary_output)
        if len(written) != len(features) or list(written.columns) != list(
            features.columns
        ):
            raise RuntimeError("A saída de atributos perdeu sua estrutura.")
        if TARGET_COLUMNS.intersection(written.columns):
            raise RuntimeError("A saída contém rótulos ou metadados futuros.")
        if written.drop(columns=["source_file", "Stime"]).isna().any(axis=None):
            raise RuntimeError("A saída contém atributos ausentes.")

        hashes_after = {
            str(source): _file_sha256(source),
            str(label_source): _file_sha256(label_source),
        }
        if hashes_before != hashes_after:
            raise RuntimeError("Um artefato de entrada foi alterado.")

        feature_columns = [
            column
            for column in features.columns
            if column not in {"source_file", "Stime"}
        ]
        report: dict[str, Any] = {
            "aggregator_version": "1.0",
            "task": "prospective_attack_prediction",
            "description": (
                "Atributos históricos calculados somente com fluxos concluídos."
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(perf_counter() - started, 3),
            "causal_contract": {
                "availability_timestamp": "Ltime",
                "window_interval": "(t - W, t]",
                "lookbacks_seconds": list(windows),
                "only_completed_flows": True,
                "absolute_time_is_feature": False,
                "group_identifier_is_feature": False,
                "target_columns_are_features": False,
            },
            "inputs": {
                "flows": {
                    "path": str(source),
                    "sha256_before": hashes_before[str(source)],
                    "sha256_after": hashes_after[str(source)],
                    "preserved": True,
                },
                "labels": {
                    "path": str(label_source),
                    "sha256_before": hashes_before[str(label_source)],
                    "sha256_after": hashes_after[str(label_source)],
                    "preserved": True,
                },
            },
            "output": {
                "path": str(destination),
                "rows": int(len(features)),
                "feature_count": int(len(feature_columns)),
                "feature_columns": feature_columns,
                "key_columns": ["source_file", "Stime"],
            },
            "feature_definitions": _feature_definitions(windows),
            "precursor_analysis": analysis,
            "validation": {
                "target_columns_absent": not bool(
                    TARGET_COLUMNS.intersection(features.columns)
                ),
                "all_features_finite": bool(
                    np.isfinite(
                        features[feature_columns].to_numpy(dtype=np.float64)
                    ).all()
                ),
                "input_hashes_preserved": True,
                "causal_boundary_tested": True,
            },
            "scientific_interpretation": {
                "analysis_type": (
                    "descriptive univariate separation; not model performance"
                ),
                "precursor_claim_proven": False,
                "warning": (
                    "Historical windows can contain completed traffic from a "
                    "previous attack period. Strong separation may reflect "
                    "campaign persistence rather than advance warning."
                ),
            },
            "next_step": (
                "Criar divisão temporal com purga e avaliar baselines em "
                "blocos futuros, mantendo o ajuste somente no treino."
            ),
        }
        temporary_report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        temporary_output.replace(destination)
        temporary_report.replace(report_destination)
        permissions = source.stat().st_mode & 0o777
        destination.chmod(permissions)
        report_destination.chmod(permissions)
    except Exception:
        temporary_output.unlink(missing_ok=True)
        temporary_report.unlink(missing_ok=True)
        raise
    return report


def _append_group_features(
    output: pd.DataFrame,
    flows: pd.DataFrame,
    windows: tuple[int, ...],
) -> None:
    end = flows["Ltime"].to_numpy(dtype=np.int64)
    queries = output["Stime"].to_numpy(dtype=np.int64)
    packets = (
        flows["Spkts"].to_numpy(dtype=np.float64)
        + flows["Dpkts"].to_numpy(dtype=np.float64)
    )
    byte_values = (
        flows["sbytes"].to_numpy(dtype=np.float64)
        + flows["dbytes"].to_numpy(dtype=np.float64)
    )
    duration = flows["dur"].to_numpy(dtype=np.float64)
    proto = flows["proto"].fillna("UNKNOWN").astype(str).to_numpy()
    state = flows["state"].fillna("UNKNOWN").astype(str).to_numpy()
    categories = {
        "src_ips": flows["srcip"].fillna("UNKNOWN").astype(str).to_numpy(),
        "dst_ips": flows["dstip"].fillna("UNKNOWN").astype(str).to_numpy(),
        "src_ports": flows["sport"].fillna("UNKNOWN").astype(str).to_numpy(),
        "dst_ports": flows["dsport"].fillna("UNKNOWN").astype(str).to_numpy(),
    }
    cumulative = {
        "packets": _cumulative(packets),
        "bytes": _cumulative(byte_values),
        "duration": _cumulative(duration),
        "duration_squared": _cumulative(duration**2),
        "completion_time": _cumulative(end.astype(np.float64)),
        "tcp": _cumulative(np.char.lower(proto.astype(str)) == "tcp"),
        "udp": _cumulative(np.char.lower(proto.astype(str)) == "udp"),
        "state_fin": _cumulative(np.char.upper(state.astype(str)) == "FIN"),
        "state_con": _cumulative(np.char.upper(state.astype(str)) == "CON"),
        "state_int": _cumulative(np.char.upper(state.astype(str)) == "INT"),
    }
    for window in windows:
        lower = np.searchsorted(end, queries - window, side="right")
        upper = np.searchsorted(end, queries, side="right")
        count = upper - lower
        count_float = count.astype(np.float64)
        total_packets = _range_sum(cumulative["packets"], lower, upper)
        total_bytes = _range_sum(cumulative["bytes"], lower, upper)
        duration_sum = _range_sum(cumulative["duration"], lower, upper)
        duration_squared = _range_sum(
            cumulative["duration_squared"], lower, upper
        )
        safe_count = np.where(count > 0, count_float, 1.0)
        duration_mean = duration_sum / safe_count
        duration_variance = np.maximum(
            duration_squared / safe_count - duration_mean**2,
            0.0,
        )
        duration_mean[count == 0] = 0.0
        duration_std = np.sqrt(duration_variance)
        duration_std[count == 0] = 0.0

        output[f"completed_flows_{window}s"] = count_float
        output[f"total_packets_{window}s"] = total_packets
        output[f"total_bytes_{window}s"] = total_bytes
        output[f"duration_mean_{window}s"] = duration_mean
        output[f"duration_std_{window}s"] = duration_std
        output[f"packets_per_second_{window}s"] = total_packets / window
        output[f"bytes_per_second_{window}s"] = total_bytes / window
        categorical = _rolling_categorical_features(
            end,
            categories,
            queries,
            window,
        )
        for name, values in categorical.items():
            output[f"{name}_{window}s"] = values
        output[f"tcp_fraction_{window}s"] = _safe_fraction(
            _range_sum(cumulative["tcp"], lower, upper),
            count_float,
        )
        output[f"udp_fraction_{window}s"] = _safe_fraction(
            _range_sum(cumulative["udp"], lower, upper),
            count_float,
        )
        for state_name in ("fin", "con", "int"):
            output[f"state_{state_name}_fraction_{window}s"] = _safe_fraction(
                _range_sum(
                    cumulative[f"state_{state_name}"],
                    lower,
                    upper,
                ),
                count_float,
            )
        midpoint = np.searchsorted(
            end,
            queries - window / 2,
            side="right",
        )
        old_count = midpoint - lower
        recent_count = upper - midpoint
        output[f"flow_rate_growth_{window}s"] = (
            recent_count - old_count
        ) / (old_count + 1.0)
        completion_sum = _range_sum(
            cumulative["completion_time"],
            lower,
            upper,
        )
        start = queries - window + 1
        relative_time_flow_sum = completion_sum - start * count_float
        sum_x = window * (window - 1) / 2
        sum_x_squared = window * (window - 1) * (2 * window - 1) / 6
        denominator = window * sum_x_squared - sum_x**2
        output[f"flow_count_trend_{window}s"] = (
            window * relative_time_flow_sum - sum_x * count_float
        ) / denominator


def _analyze_precursor_signals(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    flows: pd.DataFrame,
    *,
    lookbacks: tuple[int, ...],
) -> dict[str, Any]:
    merged = labels.merge(
        features,
        on=["source_file", "Stime"],
        how="left",
        validate="many_to_one",
    )
    feature_columns = [
        column
        for column in features.columns
        if column not in {"source_file", "Stime"}
    ]
    by_horizon = []
    for horizon, subset in merged.groupby(
        "Prediction_Horizon_Seconds",
        sort=True,
        observed=True,
    ):
        target = subset["Future_Attack_Label"].to_numpy(dtype=np.int8)
        rankings = []
        for feature in feature_columns:
            values = subset[feature].to_numpy(dtype=np.float64)
            positive = values[target == 1]
            negative = values[target == 0]
            smd = _standardized_mean_difference(positive, negative)
            auc = _safe_univariate_auc(target, values)
            rankings.append(
                {
                    "feature": feature,
                    "absolute_standardized_mean_difference": round(
                        abs(smd), 6
                    ),
                    "standardized_mean_difference": round(smd, 6),
                    "direction_free_roc_auc": round(auc, 6),
                    "positive_median": round(float(np.median(positive)), 6),
                    "negative_median": round(float(np.median(negative)), 6),
                }
            )
        rankings.sort(
            key=lambda item: (
                item["direction_free_roc_auc"],
                item["absolute_standardized_mean_difference"],
            ),
            reverse=True,
        )
        contamination = _prior_attack_window_diagnostics(
            subset[["source_file", "Stime", "Future_Attack_Label"]],
            flows,
            lookbacks,
        )
        by_horizon.append(
            {
                "horizon_seconds": int(horizon),
                "positive_rows": int(target.sum()),
                "negative_rows": int((target == 0).sum()),
                "top_univariate_features": rankings[:10],
                "completed_prior_attack_traffic": contamination,
            }
        )
    return {
        "method": (
            "univariate descriptive ROC-AUC and standardized mean difference"
        ),
        "feature_count": len(feature_columns),
        "by_horizon": by_horizon,
    }


def _prior_attack_window_diagnostics(
    references: pd.DataFrame,
    flows: pd.DataFrame,
    lookbacks: tuple[int, ...],
) -> list[dict[str, Any]]:
    references = references.reset_index(drop=True)
    results = []
    for window in lookbacks:
        counts = np.zeros(len(references), dtype=np.int64)
        for source_file, positions in references.groupby(
            "source_file",
            sort=False,
            observed=True,
        ).groups.items():
            group = flows.loc[
                flows["source_file"].eq(source_file)
            ].sort_values(["Ltime", "Stime"], kind="stable")
            end = group["Ltime"].to_numpy(dtype=np.int64)
            attacks = group["Binary_Label"].to_numpy(dtype=np.int64)
            cumulative = _cumulative(attacks)
            query = references.loc[positions, "Stime"].to_numpy(dtype=np.int64)
            lower = np.searchsorted(end, query - window, side="right")
            upper = np.searchsorted(end, query, side="right")
            counts[positions] = _range_sum(
                cumulative,
                lower,
                upper,
            ).astype(np.int64)
        target = references["Future_Attack_Label"].to_numpy(dtype=np.int8)
        results.append(
            {
                "lookback_seconds": window,
                "positive_rows_with_completed_prior_attack": int(
                    ((target == 1) & (counts > 0)).sum()
                ),
                "positive_share_with_completed_prior_attack": round(
                    float((counts[target == 1] > 0).mean())
                    if (target == 1).any()
                    else 0.0,
                    8,
                ),
                "negative_share_with_completed_prior_attack": round(
                    float((counts[target == 0] > 0).mean())
                    if (target == 0).any()
                    else 0.0,
                    8,
                ),
            }
        )
    return results


def _validate_frames(
    flows: pd.DataFrame,
    references: pd.DataFrame,
) -> None:
    missing_flows = sorted(set(FLOW_COLUMNS) - set(flows.columns))
    if missing_flows:
        raise TemporalAuditError(
            f"Colunas de fluxo obrigatórias ausentes: {missing_flows}"
        )
    missing_references = sorted(
        {"source_file", "Stime"} - set(references.columns)
    )
    if missing_references:
        raise TemporalAuditError(
            f"Chaves de referência ausentes: {missing_references}"
        )
    if flows.empty or references.empty:
        raise TemporalAuditError("Fluxos e referências não podem estar vazios.")
    if (pd.to_numeric(flows["Ltime"]) < pd.to_numeric(flows["Stime"])).any():
        raise TemporalAuditError("Ltime não pode ser anterior a Stime.")
    if references.duplicated(["source_file", "Stime"]).any():
        raise TemporalAuditError("As referências devem ser únicas.")


def _normalize_lookbacks(lookbacks: Sequence[int]) -> tuple[int, ...]:
    if not lookbacks:
        raise ValueError("Informe ao menos uma janela histórica.")
    values = []
    for lookback in lookbacks:
        if isinstance(lookback, bool) or int(lookback) != lookback:
            raise ValueError("As janelas devem conter segundos inteiros.")
        if lookback <= 1:
            raise ValueError("Cada janela deve possuir ao menos dois segundos.")
        values.append(int(lookback))
    if len(set(values)) != len(values):
        raise ValueError("As janelas históricas não podem ser repetidas.")
    return tuple(sorted(values))


def _cumulative(values: np.ndarray) -> np.ndarray:
    numeric = np.asarray(values, dtype=np.float64)
    return np.concatenate(([0.0], np.cumsum(numeric)))


def _range_sum(
    cumulative: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> np.ndarray:
    return cumulative[upper] - cumulative[lower]


def _safe_fraction(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=np.float64),
        where=denominator > 0,
    )


def _rolling_categorical_features(
    end_times: np.ndarray,
    categories: dict[str, np.ndarray],
    queries: np.ndarray,
    window: int,
) -> dict[str, np.ndarray]:
    """Calcula cardinalidades e entropias exatas com dois ponteiros."""
    names = tuple(categories)
    encoded = {
        name: pd.factorize(categories[name], sort=False)[0].astype(np.int64)
        for name in names
    }
    counters = {
        name: np.zeros(
            int(encoded[name].max()) + 1 if len(encoded[name]) else 0,
            dtype=np.int64,
        )
        for name in names
    }
    distinct = {name: 0 for name in names}
    entropy_names = {"dst_ips", "dst_ports"}
    entropy_sums = {name: 0.0 for name in entropy_names}
    lookup_index = np.arange(len(end_times) + 1, dtype=np.float64)
    count_log_count = np.zeros_like(lookup_index)
    nonzero = lookup_index > 0
    count_log_count[nonzero] = (
        lookup_index[nonzero] * np.log2(lookup_index[nonzero])
    )
    outputs = {
        f"distinct_{name}": np.zeros(len(queries), dtype=np.float64)
        for name in names
    }
    outputs["dst_ip_entropy"] = np.zeros(len(queries), dtype=np.float64)
    outputs["dst_port_entropy"] = np.zeros(len(queries), dtype=np.float64)
    left = 0
    right = 0
    total = 0
    for query_index, query in enumerate(queries):
        while right < len(end_times) and end_times[right] <= query:
            for name in names:
                code = encoded[name][right]
                old = counters[name][code]
                counters[name][code] = old + 1
                if old == 0:
                    distinct[name] += 1
                if name in entropy_names:
                    entropy_sums[name] += (
                        count_log_count[old + 1] - count_log_count[old]
                    )
            right += 1
            total += 1
        lower_boundary = query - window
        while left < right and end_times[left] <= lower_boundary:
            for name in names:
                code = encoded[name][left]
                old = counters[name][code]
                counters[name][code] = old - 1
                if old == 1:
                    distinct[name] -= 1
                if name in entropy_names:
                    entropy_sums[name] += (
                        count_log_count[old - 1] - count_log_count[old]
                    )
            left += 1
            total -= 1
        for name in names:
            outputs[f"distinct_{name}"][query_index] = distinct[name]
        if total:
            outputs["dst_ip_entropy"][query_index] = (
                np.log2(total) - entropy_sums["dst_ips"] / total
            )
            outputs["dst_port_entropy"][query_index] = (
                np.log2(total) - entropy_sums["dst_ports"] / total
            )
    return outputs


def _standardized_mean_difference(
    positive: np.ndarray,
    negative: np.ndarray,
) -> float:
    variance = (positive.var() + negative.var()) / 2
    if variance <= 0:
        return 0.0
    return float((positive.mean() - negative.mean()) / np.sqrt(variance))


def _safe_univariate_auc(target: np.ndarray, values: np.ndarray) -> float:
    if len(np.unique(target)) < 2 or len(np.unique(values)) < 2:
        return 0.5
    auc = float(roc_auc_score(target, values))
    return max(auc, 1.0 - auc)


def _feature_definitions(windows: tuple[int, ...]) -> dict[str, str]:
    definitions = {
        "completed_flows": "Quantidade de fluxos concluídos na janela.",
        "total_packets": "Soma de Spkts e Dpkts dos fluxos concluídos.",
        "total_bytes": "Soma de sbytes e dbytes dos fluxos concluídos.",
        "duration_mean": "Média de dur dos fluxos concluídos.",
        "duration_std": "Desvio populacional de dur.",
        "packets_per_second": "Total de pacotes dividido pela janela.",
        "bytes_per_second": "Total de bytes dividido pela janela.",
        "distinct_src_ips": "Origens distintas na janela.",
        "distinct_dst_ips": "Destinos distintos na janela.",
        "distinct_src_ports": "Portas de origem distintas na janela.",
        "distinct_dst_ports": "Portas de destino distintas na janela.",
        "dst_ip_entropy": "Entropia de Shannon dos destinos.",
        "dst_port_entropy": "Entropia de Shannon das portas de destino.",
        "tcp_fraction": "Proporção de fluxos TCP.",
        "udp_fraction": "Proporção de fluxos UDP.",
        "state_fin_fraction": "Proporção de fluxos com estado FIN.",
        "state_con_fraction": "Proporção de fluxos com estado CON.",
        "state_int_fraction": "Proporção de fluxos com estado INT.",
        "flow_rate_growth": "Crescimento da metade recente contra a anterior.",
        "flow_count_trend": "Inclinação linear da contagem por segundo.",
    }
    return {
        f"{name}_{window}s": description
        for window in windows
        for name, description in definitions.items()
    }


def _validate_paths(
    sources: tuple[Path, ...],
    destinations: tuple[Path, ...],
    *,
    overwrite: bool,
) -> None:
    missing = [str(path) for path in sources if not path.exists()]
    if missing:
        raise FileNotFoundError("Artefatos não encontrados: " + ", ".join(missing))
    resolved_sources = {path.resolve() for path in sources}
    resolved_destinations = [path.resolve() for path in destinations]
    if resolved_sources.intersection(resolved_destinations):
        raise ValueError("As saídas devem ser diferentes das entradas.")
    if len(set(resolved_destinations)) != len(resolved_destinations):
        raise ValueError("Atributos e relatório exigem caminhos distintos.")
    existing = [str(path) for path in destinations if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "As saídas já existem. Use --overwrite explicitamente: "
            + ", ".join(existing)
        )


def _temporary_path(destination: Path, suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(
        prefix=f".{destination.stem}-",
        suffix=suffix,
        dir=destination.parent,
        delete=False,
    ) as temporary:
        return Path(temporary.name)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="data/processed/unsw_nb15_temporal_sorted.parquet",
        help="Fluxos temporais ordenados.",
    )
    parser.add_argument(
        "--labels",
        default="data/processed/unsw_nb15_prospective_labels.parquet",
        help="Rótulos prospectivos em formato longo.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/unsw_nb15_historical_features.parquet",
        help="Atributos históricos sem alvos.",
    )
    parser.add_argument(
        "--report",
        default="reports_local/prospective/unsw_precursor_analysis.json",
        help="Relatório causal e análise descritiva.",
    )
    parser.add_argument(
        "--lookbacks",
        nargs="+",
        type=int,
        default=list(DEFAULT_LOOKBACKS),
        help="Janelas históricas em segundos.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Substitui explicitamente saídas existentes.",
    )
    args = parser.parse_args()

    report = generate_historical_feature_artifacts(
        args.input,
        args.labels,
        args.output,
        args.report,
        lookbacks=args.lookbacks,
        overwrite=args.overwrite,
    )
    print(f"Atributos salvos em: {args.output}")
    print(f"Relatório salvo em: {args.report}")
    print(
        f"Instantes: {report['output']['rows']}; "
        f"atributos: {report['output']['feature_count']}"
    )
    print(f"Próximo passo: {report['next_step']}")


if __name__ == "__main__":
    main()
