"""Auditoria dos timestamps brutos do UNSW-NB15 para previsão prospectiva.

O módulo lê somente as colunas temporais e de rastreabilidade do parquet
limpo. Ele não modifica o dataset e rejeita timestamps escalados.

Uso:
    python -m src.data.prospective.temporal_audit
    python -m src.data.prospective.temporal_audit \
        --input data/processed/unsw_nb15_cleaned.parquet \
        --output reports_local/prospective/unsw_temporal_audit.json
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq


REQUIRED_COLUMNS = ("Stime", "Ltime", "source_file", "Binary_Label")
OPTIONAL_COLUMNS = ("attack_cat",)
UNIX_SECONDS_MIN = 946_684_800  # 2000-01-01T00:00:00Z
UNIX_SECONDS_MAX = 4_102_444_800  # 2100-01-01T00:00:00Z


class TemporalAuditError(ValueError):
    """Indica que os dados não atendem ao contrato temporal prospectivo."""


def audit_unsw_temporal_frame(frame: pd.DataFrame) -> dict[str, Any]:
    """Audita timestamps não escalados de um DataFrame UNSW-NB15.

    Args:
        frame: DataFrame contendo ao menos Stime, Ltime, source_file e
            Binary_Label.

    Returns:
        Dicionário serializável com estatísticas e decisão de prontidão.

    Raises:
        TemporalAuditError: Quando faltam colunas, os timestamps não são
            numéricos ou parecem ter sido escalados.
    """
    _validate_required_columns(frame)
    if frame.empty:
        raise TemporalAuditError("O dataset temporal está vazio.")

    stime = pd.to_numeric(frame["Stime"], errors="coerce")
    ltime = pd.to_numeric(frame["Ltime"], errors="coerce")
    invalid_stime = int(stime.isna().sum())
    invalid_ltime = int(ltime.isna().sum())
    if invalid_stime or invalid_ltime:
        raise TemporalAuditError(
            "Stime e Ltime devem ser numéricos e não nulos: "
            f"Stime inválidos={invalid_stime}, Ltime inválidos={invalid_ltime}."
        )

    _validate_unscaled_unix_seconds(stime, "Stime")
    _validate_unscaled_unix_seconds(ltime, "Ltime")

    labels = pd.to_numeric(frame["Binary_Label"], errors="coerce")
    if labels.isna().any() or not set(labels.unique()).issubset({0, 1}):
        raise TemporalAuditError("Binary_Label deve conter somente 0 e 1.")

    duration = ltime - stime
    file_reports = [
        _audit_source_file(group_name, group, stime.loc[group.index], ltime.loc[group.index])
        for group_name, group in frame.groupby("source_file", sort=True, dropna=False)
    ]
    total_backward_transitions = sum(
        int(report["stime_backward_transitions"]) for report in file_reports
    )
    result: dict[str, Any] = {
        "audit_version": "1.0",
        "task": "prospective_attack_prediction",
        "timestamp_contract": {
            "source": "UNSW-NB15 temporal frame with unscaled timestamps",
            "stime_semantics": "Unix seconds at flow start",
            "ltime_semantics": "Unix seconds at flow end",
            "timezone": "UTC for human-readable conversion",
            "uses_unscaled_values": True,
            "time_columns_allowed_as_model_features": False,
        },
        "rows": int(len(frame)),
        "source_files": int(frame["source_file"].nunique(dropna=False)),
        "label_distribution": {
            str(int(label)): int(count)
            for label, count in labels.value_counts().sort_index().items()
        },
        "attack_category_distribution": _attack_category_distribution(frame),
        "stime": _series_summary(stime),
        "ltime": _series_summary(ltime),
        "duration_seconds": {
            "minimum": float(duration.min()),
            "median": float(duration.median()),
            "maximum": float(duration.max()),
            "negative_count": int((duration < 0).sum()),
            "zero_count": int((duration == 0).sum()),
        },
        "ordering": {
            "stime_backward_transitions_in_input_order": total_backward_transitions,
            "input_order_is_globally_safe": total_backward_transitions == 0,
            "required_action": (
                "Ordenar cada source_file por Stime antes de criar rótulos."
                if total_backward_transitions
                else "Preservar a ordenação por source_file e Stime."
            ),
        },
        "per_source_file": file_reports,
    }
    blocking_reasons = _blocking_reasons(result)
    result["readiness"] = {
        "usable_for_temporal_pilot": not blocking_reasons,
        "blocking_reasons": blocking_reasons,
        "next_step": (
            "Corrigir os bloqueios antes de criar rótulos prospectivos."
            if blocking_reasons
            else (
                "Ordenar por source_file e Stime, sem alterar o arquivo original."
                if total_backward_transitions
                else (
                    "Identificar transições benigno→ataque dentro de cada "
                    "source_file."
                )
            )
        ),
    }
    return result


def audit_unsw_temporal_parquet(
    input_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Lê as colunas temporais do parquet e opcionalmente persiste a auditoria."""
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {source}")

    available_columns = set(pq.read_schema(source).names)
    requested_columns = [
        column
        for column in (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS)
        if column in available_columns
    ]
    missing = [column for column in REQUIRED_COLUMNS if column not in available_columns]
    if missing:
        raise TemporalAuditError(f"Colunas temporais obrigatórias ausentes: {missing}")

    frame = pd.read_parquet(source, columns=requested_columns)
    report = audit_unsw_temporal_frame(frame)
    report["input"] = {
        "path": str(source),
        "size_bytes": int(source.stat().st_size),
        "columns_read": requested_columns,
    }
    report["generated_at"] = datetime.now(timezone.utc).isoformat()

    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return report


def _validate_required_columns(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise TemporalAuditError(f"Colunas temporais obrigatórias ausentes: {missing}")


def _validate_unscaled_unix_seconds(values: pd.Series, column: str) -> None:
    median = float(values.median())
    within_range = values.between(UNIX_SECONDS_MIN, UNIX_SECONDS_MAX)
    if not UNIX_SECONDS_MIN <= median <= UNIX_SECONDS_MAX:
        raise TemporalAuditError(
            f"{column} não parece conter Unix seconds não escalados: mediana={median}."
        )
    if not bool(within_range.all()):
        invalid = int((~within_range).sum())
        raise TemporalAuditError(
            f"{column} contém {invalid} valores fora do intervalo temporal plausível."
        )


def _series_summary(values: pd.Series) -> dict[str, Any]:
    minimum = float(values.min())
    median = float(values.median())
    maximum = float(values.max())
    return {
        "dtype": str(values.dtype),
        "minimum": minimum,
        "median": median,
        "maximum": maximum,
        "minimum_utc": _unix_to_iso(minimum),
        "median_utc": _unix_to_iso(median),
        "maximum_utc": _unix_to_iso(maximum),
        "unique_values": int(values.nunique()),
    }


def _unix_to_iso(value: float) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _audit_source_file(
    group_name: object,
    group: pd.DataFrame,
    stime: pd.Series,
    ltime: pd.Series,
) -> dict[str, Any]:
    backward = int((stime.diff().dropna() < 0).sum())
    return {
        "source_file": str(group_name),
        "rows": int(len(group)),
        "stime_minimum": float(stime.min()),
        "stime_maximum": float(stime.max()),
        "stime_minimum_utc": _unix_to_iso(float(stime.min())),
        "stime_maximum_utc": _unix_to_iso(float(stime.max())),
        "stime_monotonic_in_input_order": bool(stime.is_monotonic_increasing),
        "stime_backward_transitions": backward,
        "end_before_start_count": int((ltime < stime).sum()),
        "label_distribution": {
            str(int(label)): int(count)
            for label, count in group["Binary_Label"].value_counts().sort_index().items()
        },
    }


def _attack_category_distribution(frame: pd.DataFrame) -> dict[str, int] | None:
    if "attack_cat" not in frame.columns:
        return None
    return {
        str(category): int(count)
        for category, count in frame["attack_cat"]
        .fillna("BENIGN")
        .astype(str)
        .value_counts()
        .items()
    }


def _blocking_reasons(report: dict[str, Any]) -> list[str]:
    reasons = []
    if report["duration_seconds"]["negative_count"]:
        reasons.append("Existem fluxos com Ltime anterior a Stime.")
    if not report["source_files"]:
        reasons.append("Nenhum source_file foi identificado.")
    if set(report["label_distribution"]) != {"0", "1"}:
        reasons.append("O conjunto não contém as duas classes binárias.")
    return reasons


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="data/processed/unsw_nb15_cleaned.parquet",
        help="Parquet limpo, anterior ao escalonamento.",
    )
    parser.add_argument(
        "--output",
        default="reports_local/prospective/unsw_temporal_audit.json",
        help="Arquivo JSON da auditoria.",
    )
    args = parser.parse_args()

    report = audit_unsw_temporal_parquet(args.input, args.output)
    readiness = report["readiness"]
    print(f"Auditoria salva em: {args.output}")
    print(f"Linhas auditadas: {report['rows']}")
    print(f"Arquivos de origem: {report['source_files']}")
    print(
        "Pronto para piloto temporal: "
        f"{'sim' if readiness['usable_for_temporal_pilot'] else 'não'}"
    )
    print(f"Próximo passo: {readiness['next_step']}")


if __name__ == "__main__":
    main()
