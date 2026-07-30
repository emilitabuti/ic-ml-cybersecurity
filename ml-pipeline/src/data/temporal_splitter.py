"""Conjunto prospectivo estrito e divisão temporal com purga.

O filtro estrito remove instantes cuja janela histórica máxima contém fluxo
malicioso concluído. A divisão usa eventos futuros como âncoras cronológicas,
sem embaralhamento, e aplica purga entre treino, validação e teste.

Uso:
    python -m src.data.temporal_splitter
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
import tempfile
from typing import Any

import numpy as np
import pandas as pd

from src.data.prospective.temporal_audit import TemporalAuditError


DEFAULT_LOOKBACK_SECONDS = 120
DEFAULT_MAX_HORIZON_SECONDS = 60
DEFAULT_PURGE_SECONDS = (
    DEFAULT_LOOKBACK_SECONDS + DEFAULT_MAX_HORIZON_SECONDS
)
SPLIT_ORDER = ("train", "validation", "test")


def filter_attack_free_history(
    labels: pd.DataFrame,
    flows: pd.DataFrame,
    *,
    lookback_seconds: int = DEFAULT_LOOKBACK_SECONDS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Remove referências com ataque concluído em ``(t-W, t]``."""
    _validate_filter_inputs(labels, flows, lookback_seconds)
    references = (
        labels[["source_file", "Stime"]]
        .drop_duplicates()
        .sort_values(["source_file", "Stime"], kind="stable")
        .reset_index(drop=True)
    )
    references["Completed_Prior_Attack_Flows"] = 0
    for source_file, positions in references.groupby(
        "source_file",
        sort=False,
        observed=True,
    ).groups.items():
        group = flows.loc[
            flows["source_file"].eq(source_file)
        ].sort_values(["Ltime", "Stime"], kind="stable")
        if group.empty:
            raise TemporalAuditError(
                f"Não existem fluxos para source_file={source_file}."
            )
        end = group["Ltime"].to_numpy(dtype=np.int64)
        attacks = group["Binary_Label"].to_numpy(dtype=np.int64)
        cumulative = np.concatenate(([0], np.cumsum(attacks)))
        query = references.loc[positions, "Stime"].to_numpy(dtype=np.int64)
        lower = np.searchsorted(
            end,
            query - lookback_seconds,
            side="right",
        )
        upper = np.searchsorted(end, query, side="right")
        references.loc[positions, "Completed_Prior_Attack_Flows"] = (
            cumulative[upper] - cumulative[lower]
        )
    eligibility = references["Completed_Prior_Attack_Flows"].eq(0)
    eligible_keys = references.loc[eligibility, ["source_file", "Stime"]]
    strict = labels.merge(
        eligible_keys,
        on=["source_file", "Stime"],
        how="inner",
        validate="many_to_one",
    )
    strict["Strict_History_Attack_Free"] = True
    strict["Strict_Lookback_Seconds"] = int(lookback_seconds)
    audit = {
        "lookback_seconds": int(lookback_seconds),
        "input_temporal_units": int(len(references)),
        "eligible_temporal_units": int(eligibility.sum()),
        "excluded_temporal_units": int((~eligibility).sum()),
        "input_rows": int(len(labels)),
        "eligible_rows": int(len(strict)),
        "excluded_rows": int(len(labels) - len(strict)),
        "prior_attack_count_maximum": int(
            references["Completed_Prior_Attack_Flows"].max()
        ),
    }
    return strict, audit


def event_aware_purged_split(
    strict: pd.DataFrame,
    *,
    purge_seconds: int = DEFAULT_PURGE_SECONDS,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Divide blocos futuros usando eventos positivos como âncoras."""
    _validate_split_inputs(
        strict,
        purge_seconds=purge_seconds,
        train_fraction=train_fraction,
        validation_fraction=validation_fraction,
    )
    positive = strict.loc[strict["Future_Attack_Label"].eq(1)].copy()
    events = (
        positive[["Next_Attack_Event_ID", "Next_Attack_Onset"]]
        .drop_duplicates()
        .sort_values("Next_Attack_Onset", kind="stable")
        .reset_index(drop=True)
    )
    if events["Next_Attack_Event_ID"].duplicated().any():
        raise TemporalAuditError(
            "Um evento positivo possui mais de um instante de início."
        )
    if len(events) < 3:
        raise TemporalAuditError(
            "São necessários ao menos três eventos estritos para a divisão."
        )
    train_events = max(1, int(np.floor(len(events) * train_fraction)))
    validation_events = max(
        1,
        int(np.floor(len(events) * validation_fraction)),
    )
    if train_events + validation_events >= len(events):
        validation_events = 1
        train_events = len(events) - 2
    first_validation = train_events
    first_test = train_events + validation_events
    boundary_train_validation = _midpoint(
        events.iloc[first_validation - 1]["Next_Attack_Onset"],
        events.iloc[first_validation]["Next_Attack_Onset"],
    )
    boundary_validation_test = _midpoint(
        events.iloc[first_test - 1]["Next_Attack_Onset"],
        events.iloc[first_test]["Next_Attack_Onset"],
    )
    half_before = purge_seconds // 2
    half_after = purge_seconds - half_before
    train_max = boundary_train_validation - half_before
    validation_min = boundary_train_validation + half_after
    validation_max = boundary_validation_test - half_before
    test_min = boundary_validation_test + half_after
    if validation_min > validation_max:
        raise TemporalAuditError(
            "A purga elimina todo o bloco de validação."
        )

    times = strict["Stime"].to_numpy(dtype=np.int64)
    split = np.full(len(strict), "purged", dtype=object)
    split[times <= train_max] = "train"
    split[(times >= validation_min) & (times <= validation_max)] = "validation"
    split[times >= test_min] = "test"
    assigned = strict.copy()
    assigned.insert(0, "Split", split)
    purged = assigned.loc[assigned["Split"].eq("purged")]
    result = assigned.loc[~assigned["Split"].eq("purged")].copy()
    result["Split"] = pd.Categorical(
        result["Split"],
        categories=list(SPLIT_ORDER),
        ordered=True,
    )
    result = result.sort_values(
        ["Split", "Stime", "source_file", "Prediction_Horizon_Seconds"],
        kind="stable",
    ).reset_index(drop=True)
    _validate_partition_integrity(result, purge_seconds=purge_seconds)

    event_partitions = (
        result.loc[result["Future_Attack_Label"].eq(1)]
        .groupby("Next_Attack_Event_ID", observed=True)["Split"]
        .nunique()
    )
    if (event_partitions > 1).any():
        raise RuntimeError("Um evento positivo aparece em múltiplas partições.")
    audit = {
        "strategy": "event-anchored chronological blocks",
        "shuffle": False,
        "purge_seconds": int(purge_seconds),
        "boundaries": {
            "train_validation_midpoint": int(boundary_train_validation),
            "validation_test_midpoint": int(boundary_validation_test),
            "train_maximum_stime": int(train_max),
            "validation_minimum_stime": int(validation_min),
            "validation_maximum_stime": int(validation_max),
            "test_minimum_stime": int(test_min),
        },
        "event_allocation": {
            "total": int(len(events)),
            "train": int(train_events),
            "validation": int(validation_events),
            "test": int(len(events) - first_test),
        },
        "purged_rows": int(len(purged)),
        "assigned_rows": int(len(result)),
        "partitions": _partition_diagnostics(result),
        "positive_event_ids_disjoint": True,
        "row_keys_disjoint": True,
    }
    return result, audit


def generate_strict_temporal_split_artifacts(
    flows_path: str | Path,
    labels_path: str | Path,
    features_path: str | Path,
    output_path: str | Path,
    report_path: str | Path,
    *,
    lookback_seconds: int = DEFAULT_LOOKBACK_SECONDS,
    max_horizon_seconds: int = DEFAULT_MAX_HORIZON_SECONDS,
    purge_seconds: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Gera conjunto modelável estrito com partições auditáveis."""
    flow_source = Path(flows_path)
    label_source = Path(labels_path)
    feature_source = Path(features_path)
    destination = Path(output_path)
    report_destination = Path(report_path)
    sources = (flow_source, label_source, feature_source)
    destinations = (destination, report_destination)
    _validate_paths(sources, destinations, overwrite=overwrite)
    destination.parent.mkdir(parents=True, exist_ok=True)
    report_destination.parent.mkdir(parents=True, exist_ok=True)
    resolved_purge = (
        lookback_seconds + max_horizon_seconds
        if purge_seconds is None
        else purge_seconds
    )
    minimum_purge = lookback_seconds + max_horizon_seconds
    if resolved_purge < minimum_purge:
        raise ValueError(
            f"A purga deve possuir ao menos {minimum_purge} segundos."
        )

    started = perf_counter()
    hashes_before = {str(path): _file_sha256(path) for path in sources}
    flows = pd.read_parquet(
        flow_source,
        columns=["source_file", "Stime", "Ltime", "Binary_Label"],
    )
    labels = pd.read_parquet(label_source)
    features = pd.read_parquet(feature_source)
    strict, filter_audit = filter_attack_free_history(
        labels,
        flows,
        lookback_seconds=lookback_seconds,
    )
    split, split_audit = event_aware_purged_split(
        strict,
        purge_seconds=resolved_purge,
    )
    modeling = split.merge(
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
    if modeling[feature_columns].isna().any(axis=None):
        raise RuntimeError("Existem linhas sem atributos históricos.")

    temporary_output = _temporary_path(destination, ".tmp.parquet")
    temporary_report = _temporary_path(report_destination, ".tmp.json")
    try:
        modeling.to_parquet(
            temporary_output,
            index=False,
            compression="zstd",
        )
        written = pd.read_parquet(temporary_output)
        if len(written) != len(modeling):
            raise RuntimeError("A saída persistida perdeu linhas.")
        hashes_after = {str(path): _file_sha256(path) for path in sources}
        if hashes_before != hashes_after:
            raise RuntimeError("Um artefato de entrada foi alterado.")

        viability = _class_viability(split_audit["partitions"])
        report: dict[str, Any] = {
            "splitter_version": "1.0",
            "task": "strict_prospective_attack_prediction",
            "description": (
                "Conjunto estrito com partições temporais e purga."
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(perf_counter() - started, 3),
            "contract": {
                "strict_history_interval": "(t - lookback, t]",
                "lookback_seconds": int(lookback_seconds),
                "maximum_horizon_seconds": int(max_horizon_seconds),
                "minimum_purge_seconds": int(minimum_purge),
                "applied_purge_seconds": int(resolved_purge),
                "random_shuffle": False,
                "test_locked_for_model_selection": True,
            },
            "inputs": {
                str(path): {
                    "sha256_before": hashes_before[str(path)],
                    "sha256_after": hashes_after[str(path)],
                    "preserved": True,
                }
                for path in sources
            },
            "strict_filter": filter_audit,
            "temporal_split": split_audit,
            "output": {
                "path": str(destination),
                "rows": int(len(modeling)),
                "columns": int(len(modeling.columns)),
                "feature_columns": feature_columns,
                "target_column": "Future_Attack_Label",
                "metadata_columns": [
                    "Split",
                    "source_file",
                    "Stime",
                    "Prediction_Horizon_Seconds",
                    "Seconds_To_Attack",
                    "Next_Attack_Onset",
                    "Next_Attack_Event_ID",
                    "Strict_History_Attack_Free",
                    "Strict_Lookback_Seconds",
                ],
            },
            "validation": {
                "strict_rows_have_no_completed_prior_attack": True,
                "chronological_order": True,
                "purge_respected": True,
                "positive_events_disjoint": True,
                "input_hashes_preserved": True,
                "test_partition_locked": True,
            },
            "scientific_interpretation": {
                "strict_positive_events": int(
                    strict.loc[
                        strict["Future_Attack_Label"].eq(1),
                        "Next_Attack_Event_ID",
                    ].nunique()
                ),
                "class_viability": viability,
                "adequate_for_final_claim": False,
                "limitation": (
                    "Validation and test contain one strict event each. "
                    "Horizons without both classes cannot support binary "
                    "evaluation."
                ),
            },
            "next_step": (
                "Obter novas campanhas independentes com períodos benignos "
                "anteriores. Usar 5 s e 15 s apenas em análise exploratória, "
                "sem afirmar desempenho final."
            ),
        }
        temporary_report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        temporary_output.replace(destination)
        temporary_report.replace(report_destination)
        permissions = flow_source.stat().st_mode & 0o777
        destination.chmod(permissions)
        report_destination.chmod(permissions)
    except Exception:
        temporary_output.unlink(missing_ok=True)
        temporary_report.unlink(missing_ok=True)
        raise
    return report


def _partition_diagnostics(frame: pd.DataFrame) -> list[dict[str, Any]]:
    diagnostics = []
    for split_name in SPLIT_ORDER:
        partition = frame.loc[frame["Split"].eq(split_name)]
        horizons = []
        for horizon, group in partition.groupby(
            "Prediction_Horizon_Seconds",
            sort=True,
            observed=True,
        ):
            positive = group.loc[group["Future_Attack_Label"].eq(1)]
            horizons.append(
                {
                    "horizon_seconds": int(horizon),
                    "rows": int(len(group)),
                    "positive_rows": int(len(positive)),
                    "negative_rows": int(
                        group["Future_Attack_Label"].eq(0).sum()
                    ),
                    "positive_events": int(
                        positive["Next_Attack_Event_ID"].nunique()
                    ),
                }
            )
        diagnostics.append(
            {
                "split": split_name,
                "rows": int(len(partition)),
                "minimum_stime": int(partition["Stime"].min()),
                "maximum_stime": int(partition["Stime"].max()),
                "horizons": horizons,
            }
        )
    return diagnostics


def _class_viability(
    partitions: list[dict[str, Any]],
) -> dict[str, Any]:
    horizon_status: dict[int, dict[str, Any]] = {}
    for partition in partitions:
        for horizon in partition["horizons"]:
            value = horizon_status.setdefault(
                horizon["horizon_seconds"],
                {
                    "horizon_seconds": horizon["horizon_seconds"],
                    "partitions_with_both_classes": [],
                    "partitions_missing_a_class": [],
                    "minimum_positive_events": None,
                },
            )
            both = (
                horizon["positive_rows"] > 0
                and horizon["negative_rows"] > 0
            )
            target = (
                "partitions_with_both_classes"
                if both
                else "partitions_missing_a_class"
            )
            value[target].append(partition["split"])
            events = horizon["positive_events"]
            current = value["minimum_positive_events"]
            value["minimum_positive_events"] = (
                events if current is None else min(current, events)
            )
    statuses = [horizon_status[key] for key in sorted(horizon_status)]
    viable = [
        item["horizon_seconds"]
        for item in statuses
        if not item["partitions_missing_a_class"]
    ]
    nonviable = [
        item["horizon_seconds"]
        for item in statuses
        if item["partitions_missing_a_class"]
    ]
    return {
        "horizons_with_both_classes_in_all_partitions": viable,
        "horizons_missing_a_class": nonviable,
        "status_by_horizon": statuses,
        "adequate_for_reliable_evaluation": False,
        "reason": (
            "Even viable horizons have only one positive event in "
            "validation and test."
        ),
    }


def _validate_partition_integrity(
    frame: pd.DataFrame,
    *,
    purge_seconds: int,
) -> None:
    bounds = {}
    for split_name in SPLIT_ORDER:
        partition = frame.loc[frame["Split"].eq(split_name)]
        if partition.empty:
            raise TemporalAuditError(f"A partição {split_name} está vazia.")
        bounds[split_name] = (
            int(partition["Stime"].min()),
            int(partition["Stime"].max()),
        )
    if bounds["validation"][0] - bounds["train"][1] < purge_seconds:
        raise RuntimeError("A purga entre treino e validação não foi respeitada.")
    if bounds["test"][0] - bounds["validation"][1] < purge_seconds:
        raise RuntimeError("A purga entre validação e teste não foi respeitada.")
    keys = ["source_file", "Stime", "Prediction_Horizon_Seconds"]
    if frame.duplicated(keys).any():
        raise RuntimeError("Existem chaves repetidas nas partições.")


def _validate_filter_inputs(
    labels: pd.DataFrame,
    flows: pd.DataFrame,
    lookback_seconds: int,
) -> None:
    required_labels = {
        "source_file",
        "Stime",
        "Prediction_Horizon_Seconds",
        "Future_Attack_Label",
        "Next_Attack_Onset",
        "Next_Attack_Event_ID",
    }
    required_flows = {"source_file", "Stime", "Ltime", "Binary_Label"}
    missing_labels = sorted(required_labels - set(labels.columns))
    missing_flows = sorted(required_flows - set(flows.columns))
    if missing_labels or missing_flows:
        raise TemporalAuditError(
            "Colunas ausentes: "
            f"labels={missing_labels}, flows={missing_flows}."
        )
    if lookback_seconds <= 0:
        raise ValueError("A janela estrita deve ser positiva.")
    if labels.empty or flows.empty:
        raise TemporalAuditError("Rótulos e fluxos não podem estar vazios.")


def _validate_split_inputs(
    strict: pd.DataFrame,
    *,
    purge_seconds: int,
    train_fraction: float,
    validation_fraction: float,
) -> None:
    required = {
        "source_file",
        "Stime",
        "Prediction_Horizon_Seconds",
        "Future_Attack_Label",
        "Next_Attack_Onset",
        "Next_Attack_Event_ID",
    }
    missing = sorted(required - set(strict.columns))
    if missing:
        raise TemporalAuditError(f"Colunas estritas ausentes: {missing}")
    if purge_seconds <= 0:
        raise ValueError("A purga deve ser positiva.")
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("As frações devem pertencer ao intervalo (0, 1).")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("As frações devem reservar eventos para o teste.")


def _midpoint(left: float, right: float) -> int:
    if right <= left:
        raise TemporalAuditError("Os eventos não estão em ordem temporal estrita.")
    return int(np.floor((float(left) + float(right)) / 2))


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
        raise ValueError("Dataset e relatório exigem caminhos distintos.")
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
        "--flows",
        default="data/processed/unsw_nb15_temporal_sorted.parquet",
    )
    parser.add_argument(
        "--labels",
        default="data/processed/unsw_nb15_prospective_labels.parquet",
    )
    parser.add_argument(
        "--features",
        default="data/processed/unsw_nb15_historical_features.parquet",
    )
    parser.add_argument(
        "--output",
        default="data/processed/unsw_nb15_strict_temporal_split.parquet",
    )
    parser.add_argument(
        "--report",
        default="reports_local/prospective/unsw_strict_temporal_split.json",
    )
    parser.add_argument(
        "--lookback-seconds",
        type=int,
        default=DEFAULT_LOOKBACK_SECONDS,
    )
    parser.add_argument(
        "--max-horizon-seconds",
        type=int,
        default=DEFAULT_MAX_HORIZON_SECONDS,
    )
    parser.add_argument("--purge-seconds", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    report = generate_strict_temporal_split_artifacts(
        args.flows,
        args.labels,
        args.features,
        args.output,
        args.report,
        lookback_seconds=args.lookback_seconds,
        max_horizon_seconds=args.max_horizon_seconds,
        purge_seconds=args.purge_seconds,
        overwrite=args.overwrite,
    )
    print(f"Dataset estrito salvo em: {args.output}")
    print(f"Relatório salvo em: {args.report}")
    print(
        "Instantes estritos: "
        f"{report['strict_filter']['eligible_temporal_units']}"
    )
    for partition in report["temporal_split"]["partitions"]:
        print(f"{partition['split']}: {partition['rows']} linhas")
    print(f"Próximo passo: {report['next_step']}")


if __name__ == "__main__":
    main()
