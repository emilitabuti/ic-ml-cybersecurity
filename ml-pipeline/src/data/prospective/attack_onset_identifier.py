"""Identificação auditável de inícios de ataque no UNSW-NB15.

Fluxos com o mesmo ``source_file`` e ``Stime`` formam um único instante
observado. O instante é considerado sob ataque quando contém ao menos um
fluxo malicioso. Essa consolidação evita transições artificiais causadas pela
ordem de linhas empatadas no mesmo segundo.

Uso:
    python -m src.data.prospective.attack_onset_identifier
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
import pyarrow.parquet as pq

from src.data.prospective.temporal_audit import TemporalAuditError


REQUIRED_COLUMNS = ("source_file", "Stime", "Ltime", "Binary_Label")
OPTIONAL_COLUMNS = ("attack_cat",)


def build_attack_event_catalog(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Consolida instantes e cataloga sequências observadas de ataque."""
    _validate_frame(frame)

    working = frame.copy()
    working["Stime"] = pd.to_numeric(working["Stime"], errors="raise")
    working["Ltime"] = pd.to_numeric(working["Ltime"], errors="raise")
    working["Binary_Label"] = pd.to_numeric(
        working["Binary_Label"], errors="raise"
    ).astype("int8")
    working["_attack_ltime"] = working["Ltime"].where(
        working["Binary_Label"].eq(1)
    )

    buckets = (
        working.groupby(["source_file", "Stime"], sort=True, observed=True)
        .agg(
            flow_count=("Binary_Label", "size"),
            attack_flow_count=("Binary_Label", "sum"),
            maximum_ltime=("Ltime", "max"),
            maximum_attack_ltime=("_attack_ltime", "max"),
        )
        .reset_index()
    )
    buckets["benign_flow_count"] = (
        buckets["flow_count"] - buckets["attack_flow_count"]
    )
    buckets["attack_start_state"] = buckets["attack_flow_count"].gt(0)
    attack_end = buckets["maximum_attack_ltime"].fillna(-np.inf)
    buckets["maximum_active_attack_ltime"] = attack_end.groupby(
        buckets["source_file"],
        sort=False,
    ).cummax()
    buckets["attack_state"] = (
        buckets["maximum_active_attack_ltime"].ge(buckets["Stime"])
    ).astype("int8")
    buckets["mixed_state"] = (
        buckets["attack_state"].eq(1)
        & buckets["benign_flow_count"].gt(0)
    )
    grouped = buckets.groupby("source_file", sort=False, observed=True)
    buckets["previous_state"] = grouped["attack_state"].shift()
    buckets["previous_stime"] = grouped["Stime"].shift()
    buckets["confirmed_onset"] = (
        buckets["attack_state"].eq(1) & buckets["previous_state"].eq(0)
    )
    buckets["boundary_attack"] = (
        buckets["attack_state"].eq(1) & buckets["previous_state"].isna()
    )
    buckets["run_start"] = (
        buckets["attack_state"].eq(1)
        & ~buckets["previous_state"].eq(1)
    )
    buckets["source_event_number"] = (
        buckets.groupby("source_file", sort=False, observed=True)["run_start"]
        .cumsum()
        .astype("int64")
    )

    attack_buckets = buckets.loc[buckets["attack_state"].eq(1)].copy()
    catalog = (
        attack_buckets.groupby(
            ["source_file", "source_event_number"],
            sort=True,
            observed=True,
        )
        .agg(
            onset_stime=("Stime", "min"),
            end_stime=("Stime", "max"),
            previous_observed_stime=(
                "previous_stime",
                lambda values: values.iloc[0],
            ),
            confirmed_onset=("confirmed_onset", "first"),
            boundary_attack=("boundary_attack", "first"),
            attack_time_bins=("Stime", "size"),
            mixed_time_bins=("mixed_state", "sum"),
            total_flows=("flow_count", "sum"),
            attack_flows=("attack_flow_count", "sum"),
            benign_flows=("benign_flow_count", "sum"),
        )
        .reset_index()
    )
    catalog["seconds_since_previous_observation"] = (
        catalog["onset_stime"] - catalog["previous_observed_stime"]
    )
    catalog["observed_span_seconds"] = (
        catalog["end_stime"] - catalog["onset_stime"]
    )
    catalog["transition_type"] = catalog["confirmed_onset"].map(
        {True: "benign_to_attack", False: "attack_at_file_boundary"}
    )
    catalog["onset_utc"] = catalog["onset_stime"].map(_unix_to_iso)
    catalog["end_utc"] = catalog["end_stime"].map(_unix_to_iso)

    category_summary = _event_category_summary(working, attack_buckets)
    catalog = catalog.merge(
        category_summary,
        on=["source_file", "source_event_number"],
        how="left",
        validate="one_to_one",
    )
    catalog = catalog.sort_values(
        ["source_file", "onset_stime", "source_event_number"],
        kind="stable",
    ).reset_index(drop=True)
    catalog.insert(
        0,
        "event_id",
        [f"UNSW-E{index:06d}" for index in range(1, len(catalog) + 1)],
    )
    catalog["source_event_number"] = catalog["source_event_number"].astype(
        "int64"
    )

    diagnostics = _build_diagnostics(working, buckets, catalog)
    return catalog, diagnostics


def identify_attack_onsets_parquet(
    input_path: str | Path,
    catalog_path: str | Path,
    report_path: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Gera catálogo e relatório sem modificar o parquet temporal."""
    source = Path(input_path)
    destination = Path(catalog_path)
    report_destination = Path(report_path)
    _validate_paths(
        source,
        (destination, report_destination),
        overwrite=overwrite,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    report_destination.parent.mkdir(parents=True, exist_ok=True)

    started = perf_counter()
    source_hash_before = _file_sha256(source)
    available = set(pq.read_schema(source).names)
    missing = [column for column in REQUIRED_COLUMNS if column not in available]
    if missing:
        raise TemporalAuditError(f"Colunas obrigatórias ausentes: {missing}")
    columns = [
        column
        for column in (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS)
        if column in available
    ]
    frame = pd.read_parquet(source, columns=columns)
    catalog, diagnostics = build_attack_event_catalog(frame)

    temporary_catalog = _temporary_path(destination, ".tmp.parquet")
    temporary_report = _temporary_path(report_destination, ".tmp.json")
    try:
        catalog.to_parquet(
            temporary_catalog,
            index=False,
            compression="zstd",
        )
        written = pd.read_parquet(temporary_catalog)
        if len(written) != len(catalog) or list(written.columns) != list(
            catalog.columns
        ):
            raise RuntimeError("O catálogo persistido não preservou sua estrutura.")

        source_hash_after = _file_sha256(source)
        if source_hash_before != source_hash_after:
            raise RuntimeError(
                "O parquet temporal foi alterado durante a identificação."
            )
        report: dict[str, Any] = {
            "identifier_version": "1.0",
            "task": "prospective_attack_prediction",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(perf_counter() - started, 3),
            "method": {
                "temporal_unit": "unique source_file and Stime",
                "attack_state": (
                    "one or more Binary_Label=1 intervals cover the temporal "
                    "unit under inclusive [Stime, Ltime] semantics"
                ),
                "confirmed_onset": (
                    "previous observed temporal unit is benign-only and "
                    "current unit contains attack"
                ),
                "event": (
                    "maximal sequence of observed temporal units covered by "
                    "the union of attack intervals"
                ),
                "independent_campaign_claimed": False,
            },
            "input": {
                "path": str(source),
                "rows": int(len(frame)),
                "columns_read": columns,
                "size_bytes": int(source.stat().st_size),
                "sha256_before": source_hash_before,
                "sha256_after": source_hash_after,
                "preserved": True,
            },
            "catalog": {
                "path": str(destination),
                "rows": int(len(catalog)),
                "columns": list(catalog.columns),
            },
            "diagnostics": diagnostics,
            "scientific_interpretation": {
                "onsets_are_candidates": True,
                "campaigns_require_additional_grouping": True,
                "warning": (
                    "Fluxos benignos e maliciosos coexistem na maioria dos "
                    "instantes de ataque. Transições linha a linha não devem "
                    "ser interpretadas como campanhas independentes."
                ),
            },
            "next_step": (
                "Validar o agrupamento operacional dos eventos e criar "
                "rótulos prospectivos para 5, 15, 30 e 60 segundos."
            ),
        }
        temporary_report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        temporary_catalog.replace(destination)
        temporary_report.replace(report_destination)
        destination.chmod(source.stat().st_mode & 0o777)
        report_destination.chmod(source.stat().st_mode & 0o777)
    except Exception:
        temporary_catalog.unlink(missing_ok=True)
        temporary_report.unlink(missing_ok=True)
        raise
    return report


def _validate_frame(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise TemporalAuditError(f"Colunas obrigatórias ausentes: {missing}")
    if frame.empty:
        raise TemporalAuditError("O conjunto temporal está vazio.")
    if frame["source_file"].isna().any():
        raise TemporalAuditError("source_file não pode conter valores ausentes.")
    stime = pd.to_numeric(frame["Stime"], errors="coerce")
    ltime = pd.to_numeric(frame["Ltime"], errors="coerce")
    labels = pd.to_numeric(frame["Binary_Label"], errors="coerce")
    if stime.isna().any() or ltime.isna().any():
        raise TemporalAuditError("Stime e Ltime devem ser numéricos e não nulos.")
    if labels.isna().any() or not set(labels.unique()).issubset({0, 1}):
        raise TemporalAuditError("Binary_Label deve conter somente 0 e 1.")
    for source_file, positions in frame.groupby(
        "source_file", sort=False, observed=True
    ).groups.items():
        if not stime.loc[positions].is_monotonic_increasing:
            raise TemporalAuditError(
                f"Stime não está ordenado em source_file={source_file}."
            )


def _event_category_summary(
    frame: pd.DataFrame,
    attack_buckets: pd.DataFrame,
) -> pd.DataFrame:
    keys = ["source_file", "Stime", "source_event_number"]
    mapping = attack_buckets[keys]
    attack_rows = frame.loc[frame["Binary_Label"].eq(1)].copy()
    if "attack_cat" not in attack_rows.columns:
        events = mapping[["source_file", "source_event_number"]].drop_duplicates()
        events["primary_attack_category"] = None
        events["attack_categories"] = None
        return events

    attack_rows["attack_cat"] = (
        attack_rows["attack_cat"].fillna("UNKNOWN").astype(str)
    )
    categorized = attack_rows.merge(
        mapping,
        on=["source_file", "Stime"],
        how="left",
        validate="many_to_one",
    )
    counts = (
        categorized.groupby(
            ["source_file", "source_event_number", "attack_cat"],
            observed=True,
        )
        .size()
        .rename("count")
        .reset_index()
    )
    counts = counts.sort_values(
        [
            "source_file",
            "source_event_number",
            "count",
            "attack_cat",
        ],
        ascending=[True, True, False, True],
        kind="stable",
    )
    primary = (
        counts.drop_duplicates(["source_file", "source_event_number"])
        .rename(columns={"attack_cat": "primary_attack_category"})
        [["source_file", "source_event_number", "primary_attack_category"]]
    )
    categories = (
        counts.sort_values(
            ["source_file", "source_event_number", "attack_cat"],
            kind="stable",
        )
        .groupby(
            ["source_file", "source_event_number"],
            observed=True,
        )["attack_cat"]
        .agg("|".join)
        .rename("attack_categories")
        .reset_index()
    )
    return primary.merge(
        categories,
        on=["source_file", "source_event_number"],
        validate="one_to_one",
    )


def _build_diagnostics(
    frame: pd.DataFrame,
    buckets: pd.DataFrame,
    catalog: pd.DataFrame,
) -> dict[str, Any]:
    raw_previous = frame.groupby(
        "source_file", sort=False, observed=True
    )["Binary_Label"].shift()
    raw_transitions = int(
        (frame["Binary_Label"].eq(1) & raw_previous.eq(0)).sum()
    )
    attack_bins = int(buckets["attack_state"].sum())
    mixed_bins = int(buckets["mixed_state"].sum())
    confirmed = catalog.loc[catalog["confirmed_onset"]]
    return {
        "rows": int(len(frame)),
        "temporal_bins": int(len(buckets)),
        "attack_temporal_bins": attack_bins,
        "attack_start_temporal_bins": int(
            buckets["attack_start_state"].sum()
        ),
        "active_attack_bins_without_attack_start": int(
            (
                buckets["attack_state"].eq(1)
                & ~buckets["attack_start_state"]
            ).sum()
        ),
        "benign_only_temporal_bins": int(
            buckets["attack_state"].eq(0).sum()
        ),
        "mixed_temporal_bins": mixed_bins,
        "mixed_share_of_attack_bins": (
            round(mixed_bins / attack_bins, 8) if attack_bins else 0.0
        ),
        "raw_row_benign_to_attack_transitions": raw_transitions,
        "confirmed_timestamp_onsets": int(catalog["confirmed_onset"].sum()),
        "attack_runs_at_file_boundary": int(catalog["boundary_attack"].sum()),
        "cataloged_attack_runs": int(len(catalog)),
        "by_source_file": _per_source_diagnostics(buckets, catalog),
        "onset_gap_seconds": _numeric_summary(
            confirmed["seconds_since_previous_observation"]
        ),
        "event_observed_span_seconds": _numeric_summary(
            catalog["observed_span_seconds"]
        ),
        "event_attack_time_bins": _numeric_summary(
            catalog["attack_time_bins"]
        ),
        "primary_attack_category_distribution": {
            str(category): int(count)
            for category, count in catalog["primary_attack_category"]
            .fillna("UNKNOWN")
            .value_counts()
            .sort_index()
            .items()
        },
    }


def _per_source_diagnostics(
    buckets: pd.DataFrame,
    catalog: pd.DataFrame,
) -> list[dict[str, Any]]:
    results = []
    for source_file, group in buckets.groupby(
        "source_file", sort=True, observed=True
    ):
        events = catalog.loc[catalog["source_file"].eq(source_file)]
        results.append(
            {
                "source_file": str(source_file),
                "temporal_bins": int(len(group)),
                "attack_temporal_bins": int(group["attack_state"].sum()),
                "attack_start_temporal_bins": int(
                    group["attack_start_state"].sum()
                ),
                "mixed_temporal_bins": int(group["mixed_state"].sum()),
                "confirmed_timestamp_onsets": int(
                    events["confirmed_onset"].sum()
                ),
                "boundary_attack_runs": int(events["boundary_attack"].sum()),
            }
        )
    return results


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


def _unix_to_iso(value: float | int) -> str:
    return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()


def _validate_paths(
    source: Path,
    destinations: tuple[Path, ...],
    *,
    overwrite: bool,
) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {source}")
    resolved_source = source.resolve()
    resolved_destinations = [path.resolve() for path in destinations]
    if resolved_source in resolved_destinations:
        raise ValueError("As saídas devem ser diferentes do parquet de entrada.")
    if len(set(resolved_destinations)) != len(resolved_destinations):
        raise ValueError("O catálogo e o relatório devem usar caminhos distintos.")
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
        help="Parquet ordenado por source_file e Stime.",
    )
    parser.add_argument(
        "--catalog",
        default="reports_local/prospective/unsw_attack_onsets.parquet",
        help="Catálogo dos eventos observados.",
    )
    parser.add_argument(
        "--report",
        default="reports_local/prospective/unsw_attack_onsets.json",
        help="Relatório metodológico e estatístico.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Substitui explicitamente saídas existentes.",
    )
    args = parser.parse_args()

    report = identify_attack_onsets_parquet(
        args.input,
        args.catalog,
        args.report,
        overwrite=args.overwrite,
    )
    diagnostics = report["diagnostics"]
    print(f"Catálogo salvo em: {args.catalog}")
    print(f"Relatório salvo em: {args.report}")
    print(
        "Transições linha a linha: "
        f"{diagnostics['raw_row_benign_to_attack_transitions']}"
    )
    print(
        "Inícios confirmados por instante: "
        f"{diagnostics['confirmed_timestamp_onsets']}"
    )
    print(f"Próximo passo: {report['next_step']}")


if __name__ == "__main__":
    main()
