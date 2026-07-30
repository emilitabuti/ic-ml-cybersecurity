"""Criação de rótulos prospectivos para previsão antecipada.

O rótulo é positivo somente quando o instante atual é benigno e o próximo
início confirmado ocorre em ``(t, t + H]``. Inícios de outros arquivos nunca
são usados.

Uso:
    python -m src.features.prospective_labeler
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

from src.data.prospective.temporal_audit import TemporalAuditError


DEFAULT_HORIZONS = (5, 15, 30, 60)


def create_prospective_labels(
    frame: pd.DataFrame,
    timestamp_column: str = "Stime",
    end_timestamp_column: str = "Ltime",
    label_column: str = "Binary_Label",
    group_columns: Sequence[str] = ("source_file",),
    horizon_seconds: int = 30,
    *,
    onsets: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Cria rótulos para um horizonte e remove instantes com ataque ativo."""
    groups = tuple(group_columns)
    _validate_inputs(
        frame,
        timestamp_column=timestamp_column,
        end_timestamp_column=end_timestamp_column,
        label_column=label_column,
        group_columns=groups,
        horizon_seconds=horizon_seconds,
    )
    buckets = _build_temporal_buckets(
        frame,
        timestamp_column=timestamp_column,
        end_timestamp_column=end_timestamp_column,
        label_column=label_column,
        group_columns=groups,
    )
    onset_frame = _prepare_onsets(
        onsets,
        buckets=buckets,
        timestamp_column=timestamp_column,
        group_columns=groups,
    )
    eligible = buckets.loc[~buckets["Current_Attack_Active"]].copy()
    labeled_parts: list[pd.DataFrame] = []
    onset_groups = {
        _group_key(key): group.sort_values("onset_stime", kind="stable")
        for key, group in onset_frame.groupby(
            list(groups),
            sort=False,
            observed=True,
        )
    }
    for key, group in eligible.groupby(
        list(groups),
        sort=False,
        observed=True,
    ):
        part = group.copy()
        candidates = onset_groups.get(_group_key(key))
        next_times = np.full(len(part), np.nan, dtype=np.float64)
        next_events = np.full(len(part), None, dtype=object)
        if candidates is not None and not candidates.empty:
            onset_times = candidates["onset_stime"].to_numpy(dtype=np.float64)
            times = part[timestamp_column].to_numpy(dtype=np.float64)
            positions = np.searchsorted(onset_times, times, side="right")
            valid = positions < len(onset_times)
            next_times[valid] = onset_times[positions[valid]]
            if "event_id" in candidates.columns:
                event_ids = candidates["event_id"].to_numpy(dtype=object)
                next_events[valid] = event_ids[positions[valid]]
        seconds = next_times - part[timestamp_column].to_numpy(dtype=np.float64)
        positive = (
            np.isfinite(seconds)
            & (seconds > 0)
            & (seconds <= horizon_seconds)
        )
        part["Prediction_Horizon_Seconds"] = int(horizon_seconds)
        part["Future_Attack_Label"] = positive.astype("int8")
        part["Seconds_To_Attack"] = seconds
        part["Next_Attack_Onset"] = next_times
        part["Next_Attack_Event_ID"] = next_events
        labeled_parts.append(part)

    if not labeled_parts:
        return _empty_label_frame(
            buckets,
            timestamp_column=timestamp_column,
        )
    result = pd.concat(labeled_parts, ignore_index=True)
    result = result.sort_values(
        [*groups, timestamp_column],
        kind="stable",
    ).reset_index(drop=True)
    return result


def create_multi_horizon_labels(
    frame: pd.DataFrame,
    horizons: Sequence[int] = DEFAULT_HORIZONS,
    *,
    timestamp_column: str = "Stime",
    end_timestamp_column: str = "Ltime",
    label_column: str = "Binary_Label",
    group_columns: Sequence[str] = ("source_file",),
    onsets: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Empilha rótulos independentes para múltiplos horizontes."""
    normalized = _normalize_horizons(horizons)
    parts = [
        create_prospective_labels(
            frame,
            timestamp_column=timestamp_column,
            end_timestamp_column=end_timestamp_column,
            label_column=label_column,
            group_columns=group_columns,
            horizon_seconds=horizon,
            onsets=onsets,
        )
        for horizon in normalized
    ]
    result = pd.concat(parts, ignore_index=True)
    return result.sort_values(
        [*group_columns, timestamp_column, "Prediction_Horizon_Seconds"],
        kind="stable",
    ).reset_index(drop=True)


def generate_prospective_label_artifacts(
    input_path: str | Path,
    onset_catalog_path: str | Path,
    output_path: str | Path,
    report_path: str | Path,
    *,
    horizons: Sequence[int] = DEFAULT_HORIZONS,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Gera dataset rotulado e relatório sem alterar os artefatos de entrada."""
    source = Path(input_path)
    onset_source = Path(onset_catalog_path)
    destination = Path(output_path)
    report_destination = Path(report_path)
    _validate_paths(
        (source, onset_source),
        (destination, report_destination),
        overwrite=overwrite,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    report_destination.parent.mkdir(parents=True, exist_ok=True)
    normalized_horizons = _normalize_horizons(horizons)

    started = perf_counter()
    input_hashes_before = {
        str(source): _file_sha256(source),
        str(onset_source): _file_sha256(onset_source),
    }
    required = {"source_file", "Stime", "Ltime", "Binary_Label"}
    available = set(pq.read_schema(source).names)
    missing = sorted(required - available)
    if missing:
        raise TemporalAuditError(f"Colunas obrigatórias ausentes: {missing}")
    frame = pd.read_parquet(
        source,
        columns=["source_file", "Stime", "Ltime", "Binary_Label"],
    )
    onsets = pd.read_parquet(onset_source)
    labels = create_multi_horizon_labels(
        frame,
        normalized_horizons,
        onsets=onsets,
    )
    diagnostics = _build_diagnostics(
        frame,
        labels,
        onsets,
        horizons=normalized_horizons,
    )

    temporary_output = _temporary_path(destination, ".tmp.parquet")
    temporary_report = _temporary_path(report_destination, ".tmp.json")
    try:
        labels.to_parquet(
            temporary_output,
            index=False,
            compression="zstd",
        )
        written = pd.read_parquet(temporary_output)
        if len(written) != len(labels) or list(written.columns) != list(
            labels.columns
        ):
            raise RuntimeError("A saída rotulada não preservou sua estrutura.")
        _validate_persisted_labels(written, normalized_horizons)

        input_hashes_after = {
            str(source): _file_sha256(source),
            str(onset_source): _file_sha256(onset_source),
        }
        if input_hashes_before != input_hashes_after:
            raise RuntimeError("Um artefato de entrada foi alterado.")

        report: dict[str, Any] = {
            "labeler_version": "1.0",
            "task": "prospective_attack_prediction",
            "description": (
                "Rótulos prospectivos por horizonte para instantes benignos."
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(perf_counter() - started, 3),
            "contract": {
                "eligible_state": "benign-only temporal unit",
                "active_attack_semantics": (
                    "any attack interval covering t under inclusive "
                    "[Stime, Ltime]"
                ),
                "positive_interval": "(t, t + H]",
                "group_boundary": "source_file",
                "active_attack_units_excluded": True,
                "future_columns_are_targets_not_features": [
                    "Future_Attack_Label",
                    "Seconds_To_Attack",
                    "Next_Attack_Onset",
                    "Next_Attack_Event_ID",
                ],
                "horizons_seconds": list(normalized_horizons),
            },
            "inputs": {
                "temporal_dataset": {
                    "path": str(source),
                    "sha256_before": input_hashes_before[str(source)],
                    "sha256_after": input_hashes_after[str(source)],
                    "preserved": True,
                },
                "onset_catalog": {
                    "path": str(onset_source),
                    "sha256_before": input_hashes_before[str(onset_source)],
                    "sha256_after": input_hashes_after[str(onset_source)],
                    "preserved": True,
                },
            },
            "output": {
                "path": str(destination),
                "rows": int(len(labels)),
                "columns": list(labels.columns),
            },
            "diagnostics": diagnostics,
            "validation": {
                "all_output_units_are_benign": bool(
                    (~labels["Current_Attack_Active"]).all()
                ),
                "all_positive_seconds_are_within_horizon": bool(
                    (
                        labels.loc[
                            labels["Future_Attack_Label"].eq(1),
                            "Seconds_To_Attack",
                        ]
                        <= labels.loc[
                            labels["Future_Attack_Label"].eq(1),
                            "Prediction_Horizon_Seconds",
                        ]
                    ).all()
                ),
                "no_nonfuture_positive": bool(
                    (
                        labels.loc[
                            labels["Future_Attack_Label"].eq(1),
                            "Seconds_To_Attack",
                        ]
                        > 0
                    ).all()
                ),
                "group_boundaries_respected": True,
            },
            "next_step": (
                "Construir atributos históricos anteriores a t e verificar "
                "se os eventos possuem sinais precursores observáveis."
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


def _build_temporal_buckets(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
    end_timestamp_column: str,
    label_column: str,
    group_columns: tuple[str, ...],
) -> pd.DataFrame:
    working = frame[
        [
            *group_columns,
            timestamp_column,
            end_timestamp_column,
            label_column,
        ]
    ].copy()
    working[timestamp_column] = pd.to_numeric(
        working[timestamp_column], errors="raise"
    )
    working[label_column] = pd.to_numeric(
        working[label_column], errors="raise"
    ).astype("int8")
    working[end_timestamp_column] = pd.to_numeric(
        working[end_timestamp_column], errors="raise"
    )
    working["_attack_end"] = working[end_timestamp_column].where(
        working[label_column].eq(1)
    )
    buckets = (
        working.groupby(
            [*group_columns, timestamp_column],
            sort=True,
            observed=True,
        )
        .agg(
            Flow_Count=(label_column, "size"),
            Attack_Flow_Count=(label_column, "sum"),
            Attack_Maximum_Ltime=("_attack_end", "max"),
        )
        .reset_index()
    )
    buckets["Benign_Flow_Count"] = (
        buckets["Flow_Count"] - buckets["Attack_Flow_Count"]
    )
    attack_end = buckets["Attack_Maximum_Ltime"].fillna(-np.inf)
    group_values = [buckets[column] for column in group_columns]
    buckets["Maximum_Active_Attack_Ltime"] = attack_end.groupby(
        group_values,
        sort=False,
    ).cummax()
    buckets["Current_Attack_Active"] = (
        buckets["Maximum_Active_Attack_Ltime"].ge(
            buckets[timestamp_column]
        )
    )
    return buckets


def _prepare_onsets(
    onsets: pd.DataFrame | None,
    *,
    buckets: pd.DataFrame,
    timestamp_column: str,
    group_columns: tuple[str, ...],
) -> pd.DataFrame:
    if onsets is None:
        states = buckets[
            [*group_columns, timestamp_column, "Current_Attack_Active"]
        ].copy()
        previous = states.groupby(
            list(group_columns),
            sort=False,
            observed=True,
        )["Current_Attack_Active"].shift()
        derived = states.loc[
            states["Current_Attack_Active"] & previous.eq(False),
            [*group_columns, timestamp_column],
        ].rename(columns={timestamp_column: "onset_stime"})
        derived["event_id"] = [
            f"DERIVED-E{index:06d}"
            for index in range(1, len(derived) + 1)
        ]
        return derived.reset_index(drop=True)

    required = {*group_columns, "onset_stime"}
    missing = sorted(required - set(onsets.columns))
    if missing:
        raise TemporalAuditError(
            f"Colunas obrigatórias ausentes no catálogo: {missing}"
        )
    prepared = onsets.copy()
    if "confirmed_onset" in prepared.columns:
        prepared = prepared.loc[prepared["confirmed_onset"].astype(bool)]
    prepared["onset_stime"] = pd.to_numeric(
        prepared["onset_stime"], errors="raise"
    )
    keys = [*group_columns, "onset_stime"]
    if prepared.duplicated(keys).any():
        raise TemporalAuditError(
            "O catálogo possui inícios duplicados no mesmo grupo e instante."
        )
    attack_units = buckets.loc[
        buckets["Attack_Flow_Count"].gt(0),
        [*group_columns, timestamp_column],
    ].rename(columns={timestamp_column: "onset_stime"})
    validation = prepared[keys].merge(
        attack_units,
        on=keys,
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    if validation["_merge"].ne("both").any():
        raise TemporalAuditError(
            "O catálogo contém início sem ataque no conjunto temporal."
        )
    columns = [*group_columns, "onset_stime"]
    if "event_id" in prepared.columns:
        columns.append("event_id")
    return prepared[columns].sort_values(keys, kind="stable").reset_index(
        drop=True
    )


def _validate_inputs(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
    end_timestamp_column: str,
    label_column: str,
    group_columns: tuple[str, ...],
    horizon_seconds: int,
) -> None:
    if not group_columns:
        raise ValueError("Ao menos uma coluna de agrupamento é obrigatória.")
    missing = [
        column
        for column in (
            *group_columns,
            timestamp_column,
            end_timestamp_column,
            label_column,
        )
        if column not in frame.columns
    ]
    if missing:
        raise TemporalAuditError(f"Colunas obrigatórias ausentes: {missing}")
    if frame.empty:
        raise TemporalAuditError("O conjunto temporal está vazio.")
    if isinstance(horizon_seconds, bool) or int(horizon_seconds) != horizon_seconds:
        raise ValueError("O horizonte deve ser um número inteiro de segundos.")
    if horizon_seconds <= 0:
        raise ValueError("O horizonte deve ser maior que zero.")
    timestamps = pd.to_numeric(frame[timestamp_column], errors="coerce")
    end_timestamps = pd.to_numeric(
        frame[end_timestamp_column], errors="coerce"
    )
    labels = pd.to_numeric(frame[label_column], errors="coerce")
    if timestamps.isna().any() or end_timestamps.isna().any():
        raise TemporalAuditError("Os timestamps devem ser numéricos e não nulos.")
    if (end_timestamps < timestamps).any():
        raise TemporalAuditError("Ltime não pode ser anterior a Stime.")
    if labels.isna().any() or not set(labels.unique()).issubset({0, 1}):
        raise TemporalAuditError("O rótulo atual deve conter somente 0 e 1.")
    if frame[list(group_columns)].isna().any(axis=None):
        raise TemporalAuditError("As colunas de agrupamento não aceitam nulos.")
    for key, positions in frame.groupby(
        list(group_columns),
        sort=False,
        observed=True,
    ).groups.items():
        if not timestamps.loc[positions].is_monotonic_increasing:
            raise TemporalAuditError(
                f"Os timestamps não estão ordenados no grupo {_group_key(key)}."
            )


def _normalize_horizons(horizons: Sequence[int]) -> tuple[int, ...]:
    if not horizons:
        raise ValueError("Informe ao menos um horizonte.")
    normalized = []
    for horizon in horizons:
        if isinstance(horizon, bool) or int(horizon) != horizon or horizon <= 0:
            raise ValueError("Todos os horizontes devem ser inteiros positivos.")
        normalized.append(int(horizon))
    if len(set(normalized)) != len(normalized):
        raise ValueError("Os horizontes não podem ser repetidos.")
    return tuple(sorted(normalized))


def _build_diagnostics(
    frame: pd.DataFrame,
    labels: pd.DataFrame,
    onsets: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
) -> dict[str, Any]:
    buckets = _build_temporal_buckets(
        frame,
        timestamp_column="Stime",
        end_timestamp_column="Ltime",
        label_column="Binary_Label",
        group_columns=("source_file",),
    )
    confirmed_onsets = (
        onsets.loc[onsets["confirmed_onset"].astype(bool)]
        if "confirmed_onset" in onsets.columns
        else onsets
    )
    by_horizon = []
    for horizon in horizons:
        subset = labels.loc[
            labels["Prediction_Horizon_Seconds"].eq(horizon)
        ]
        positive = subset.loc[subset["Future_Attack_Label"].eq(1)]
        covered_events = int(positive["Next_Attack_Event_ID"].nunique())
        by_horizon.append(
            {
                "horizon_seconds": horizon,
                "eligible_temporal_bins": int(len(subset)),
                "positive_labels": int(len(positive)),
                "negative_labels": int(
                    subset["Future_Attack_Label"].eq(0).sum()
                ),
                "positive_prevalence": round(
                    float(subset["Future_Attack_Label"].mean()),
                    8,
                ),
                "covered_onset_events": covered_events,
                "onset_event_coverage": round(
                    covered_events / len(confirmed_onsets),
                    8,
                )
                if len(confirmed_onsets)
                else 0.0,
                "seconds_to_attack_for_positives": _numeric_summary(
                    positive["Seconds_To_Attack"]
                ),
            }
        )
    return {
        "input_rows": int(len(frame)),
        "temporal_bins": int(len(buckets)),
        "eligible_benign_only_bins": int(
            (~buckets["Current_Attack_Active"]).sum()
        ),
        "excluded_attack_active_bins": int(
            buckets["Current_Attack_Active"].sum()
        ),
        "confirmed_onsets": int(len(confirmed_onsets)),
        "output_rows": int(len(labels)),
        "rows_without_future_onset_per_horizon": int(
            labels.loc[
                labels["Prediction_Horizon_Seconds"].eq(horizons[0]),
                "Seconds_To_Attack",
            ].isna().sum()
        ),
        "by_horizon": by_horizon,
        "examples": _validation_examples(labels, horizons),
    }


def _validation_examples(
    labels: pd.DataFrame,
    horizons: tuple[int, ...],
) -> list[dict[str, Any]]:
    examples = []
    for horizon in horizons:
        subset = labels.loc[
            labels["Prediction_Horizon_Seconds"].eq(horizon)
        ]
        positive = subset.loc[subset["Future_Attack_Label"].eq(1)]
        negative = subset.loc[
            subset["Future_Attack_Label"].eq(0)
            & subset["Seconds_To_Attack"].notna()
        ]
        for kind, candidates in (("positive", positive), ("negative", negative)):
            if candidates.empty:
                continue
            row = candidates.iloc[0]
            examples.append(
                {
                    "kind": kind,
                    "source_file": str(row["source_file"]),
                    "stime": int(row["Stime"]),
                    "horizon_seconds": horizon,
                    "seconds_to_attack": float(row["Seconds_To_Attack"]),
                    "future_attack_label": int(row["Future_Attack_Label"]),
                    "rule_verified": bool(
                        (kind == "positive" and 0 < row["Seconds_To_Attack"] <= horizon)
                        or (kind == "negative" and row["Seconds_To_Attack"] > horizon)
                    ),
                }
            )
    return examples


def _validate_persisted_labels(
    labels: pd.DataFrame,
    horizons: tuple[int, ...],
) -> None:
    if set(labels["Prediction_Horizon_Seconds"].unique()) != set(horizons):
        raise RuntimeError("A saída não contém todos os horizontes solicitados.")
    if labels["Current_Attack_Active"].any():
        raise RuntimeError("A saída contém instante com ataque ativo.")
    valid_labels = set(labels["Future_Attack_Label"].unique())
    if not valid_labels.issubset({0, 1}):
        raise RuntimeError("A saída contém rótulos prospectivos inválidos.")


def _empty_label_frame(
    buckets: pd.DataFrame,
    *,
    timestamp_column: str,
) -> pd.DataFrame:
    result = buckets.iloc[0:0].copy()
    result["Prediction_Horizon_Seconds"] = pd.Series(dtype="int64")
    result["Future_Attack_Label"] = pd.Series(dtype="int8")
    result["Seconds_To_Attack"] = pd.Series(dtype="float64")
    result["Next_Attack_Onset"] = pd.Series(dtype="float64")
    result["Next_Attack_Event_ID"] = pd.Series(dtype="object")
    return result


def _numeric_summary(values: pd.Series) -> dict[str, float | int | None]:
    clean = values.dropna()
    if clean.empty:
        return {
            "count": 0,
            "minimum": None,
            "median": None,
            "p95": None,
            "maximum": None,
        }
    return {
        "count": int(len(clean)),
        "minimum": float(clean.min()),
        "median": float(clean.median()),
        "p95": float(clean.quantile(0.95)),
        "maximum": float(clean.max()),
    }


def _group_key(value: Any) -> tuple[Any, ...]:
    return value if isinstance(value, tuple) else (value,)


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
        raise ValueError("As saídas devem ser diferentes dos artefatos de entrada.")
    if len(set(resolved_destinations)) != len(resolved_destinations):
        raise ValueError("Dataset e relatório devem usar caminhos distintos.")
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
        help="Parquet temporal ordenado.",
    )
    parser.add_argument(
        "--onsets",
        default="reports_local/prospective/unsw_attack_onsets.parquet",
        help="Catálogo dos inícios confirmados.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/unsw_nb15_prospective_labels.parquet",
        help="Dataset de rótulos em formato longo.",
    )
    parser.add_argument(
        "--report",
        default="reports_local/prospective/unsw_prospective_labels.json",
        help="Relatório de distribuição dos rótulos.",
    )
    parser.add_argument(
        "--horizons",
        nargs="+",
        type=int,
        default=list(DEFAULT_HORIZONS),
        help="Horizontes de previsão em segundos.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Substitui explicitamente saídas existentes.",
    )
    args = parser.parse_args()

    report = generate_prospective_label_artifacts(
        args.input,
        args.onsets,
        args.output,
        args.report,
        horizons=args.horizons,
        overwrite=args.overwrite,
    )
    print(f"Rótulos salvos em: {args.output}")
    print(f"Relatório salvo em: {args.report}")
    for item in report["diagnostics"]["by_horizon"]:
        print(
            f"H={item['horizon_seconds']}s: "
            f"positivos={item['positive_labels']}, "
            f"negativos={item['negative_labels']}, "
            f"eventos cobertos={item['covered_onset_events']}"
        )
    print(f"Próximo passo: {report['next_step']}")


if __name__ == "__main__":
    main()
