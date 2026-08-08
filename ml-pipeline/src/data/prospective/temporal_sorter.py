"""Ordenação temporal não destrutiva do UNSW-NB15.

O módulo preserva o parquet limpo e cria uma cópia ordenada por arquivo,
instante inicial, instante final e posição original. A posição original é
usada somente para desempate e não é persistida.

Uso:
    python -m src.data.prospective.temporal_sorter
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
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.prospective.temporal_audit import (
    REQUIRED_COLUMNS,
    TemporalAuditError,
    audit_unsw_temporal_frame,
)


HELPER_INDEX = "__temporal_original_row_index"
SORT_KEYS = (
    ("source_file", "ascending"),
    ("Stime", "ascending"),
    ("Ltime", "ascending"),
    (HELPER_INDEX, "ascending"),
)


def sort_unsw_temporal_parquet(
    input_path: str | Path,
    output_path: str | Path,
    report_path: str | Path | None = None,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Cria uma cópia temporalmente ordenada sem alterar o parquet original."""
    source = Path(input_path)
    destination = Path(output_path)
    _validate_paths(source, destination, overwrite=overwrite)
    destination.parent.mkdir(parents=True, exist_ok=True)

    started = perf_counter()
    source_hash_before = _file_sha256(source)
    source_size_before = source.stat().st_size
    table = pq.read_table(source)
    _validate_schema(table)
    input_schema = table.schema

    input_temporal = table.select(
        [column for column in (*REQUIRED_COLUMNS, "attack_cat") if column in table.column_names]
    ).to_pandas()
    input_audit = audit_unsw_temporal_frame(input_temporal)
    if not input_audit["readiness"]["usable_for_temporal_pilot"]:
        raise TemporalAuditError(
            "O dataset de entrada possui bloqueios temporais: "
            + "; ".join(input_audit["readiness"]["blocking_reasons"])
        )

    table_with_index = table.append_column(
        HELPER_INDEX,
        pa.array(np.arange(table.num_rows, dtype=np.int64)),
    )
    sorted_table = table_with_index.sort_by(list(SORT_KEYS)).drop_columns(
        [HELPER_INDEX]
    )
    _validate_preserved_schema(input_schema, sorted_table.schema)

    temporary_path = _temporary_parquet_path(destination)
    try:
        pq.write_table(
            sorted_table,
            temporary_path,
            compression="zstd",
            use_dictionary=True,
            write_statistics=True,
        )
        _validate_written_parquet(
            temporary_path,
            expected_rows=table.num_rows,
            expected_schema=input_schema,
        )
        output_temporal = pq.read_table(
            temporary_path,
            columns=[
                column
                for column in (*REQUIRED_COLUMNS, "attack_cat")
                if column in sorted_table.column_names
            ],
        ).to_pandas()
        output_audit = audit_unsw_temporal_frame(output_temporal)
        backward = output_audit["ordering"][
            "stime_backward_transitions_in_input_order"
        ]
        if backward != 0:
            raise TemporalAuditError(
                "A saída ainda contém regressões temporais: "
                f"{backward} transições."
            )
        temporary_path.replace(destination)
        destination.chmod(source.stat().st_mode & 0o777)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    source_hash_after = _file_sha256(source)
    if source_hash_before != source_hash_after:
        raise RuntimeError("O parquet original foi alterado durante a ordenação.")

    report: dict[str, Any] = {
        "sort_version": "1.0",
        "task": "prospective_attack_prediction",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(perf_counter() - started, 3),
        "sort_keys": [f"{column} {direction}" for column, direction in SORT_KEYS],
        "stable_tie_breaker_persisted": False,
        "input": {
            "path": str(source),
            "rows": int(table.num_rows),
            "columns": int(table.num_columns),
            "size_bytes": int(source_size_before),
            "sha256_before": source_hash_before,
            "sha256_after": source_hash_after,
            "preserved": True,
            "backward_transitions_before": input_audit["ordering"][
                "stime_backward_transitions_in_input_order"
            ],
        },
        "output": {
            "path": str(destination),
            "rows": int(sorted_table.num_rows),
            "columns": int(sorted_table.num_columns),
            "size_bytes": int(destination.stat().st_size),
            "sha256": _file_sha256(destination),
            "schema_preserved": True,
            "backward_transitions_after": output_audit["ordering"][
                "stime_backward_transitions_in_input_order"
            ],
            "source_files": output_audit["source_files"],
            "label_distribution": output_audit["label_distribution"],
        },
        "validation": {
            "row_count_preserved": table.num_rows == sorted_table.num_rows,
            "column_count_preserved": table.num_columns == sorted_table.num_columns,
            "input_hash_preserved": source_hash_before == source_hash_after,
            "monotonic_within_source_file": all(
                item["stime_monotonic_in_input_order"]
                for item in output_audit["per_source_file"]
            ),
            "ready_for_onset_identification": True,
        },
        "next_step": (
            "Identificar transições benigno->ataque dentro de cada source_file "
            "no parquet temporal ordenado."
        ),
    }
    if report_path is not None:
        report_destination = Path(report_path)
        report_destination.parent.mkdir(parents=True, exist_ok=True)
        report_destination.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return report


def _validate_paths(source: Path, destination: Path, *, overwrite: bool) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {source}")
    if source.resolve() == destination.resolve():
        raise ValueError("A saída deve ser diferente do parquet original.")
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"A saída já existe: {destination}. Use --overwrite explicitamente."
        )


def _validate_schema(table: pa.Table) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in table.column_names]
    if missing:
        raise TemporalAuditError(f"Colunas temporais obrigatórias ausentes: {missing}")
    if HELPER_INDEX in table.column_names:
        raise TemporalAuditError(
            f"O dataset já contém a coluna auxiliar reservada {HELPER_INDEX}."
        )


def _validate_preserved_schema(source: pa.Schema, output: pa.Schema) -> None:
    if source.names != output.names:
        raise RuntimeError("A ordenação alterou os nomes ou a ordem das colunas.")
    source_types = [field.type for field in source]
    output_types = [field.type for field in output]
    if source_types != output_types:
        raise RuntimeError("A ordenação alterou os tipos das colunas.")


def _validate_written_parquet(
    path: Path,
    *,
    expected_rows: int,
    expected_schema: pa.Schema,
) -> None:
    metadata = pq.read_metadata(path)
    if metadata.num_rows != expected_rows:
        raise RuntimeError(
            "A saída possui quantidade incorreta de linhas: "
            f"esperado={expected_rows}, recebido={metadata.num_rows}."
        )
    written_schema = pq.read_schema(path)
    _validate_preserved_schema(expected_schema, written_schema)


def _temporary_parquet_path(destination: Path) -> Path:
    with tempfile.NamedTemporaryFile(
        prefix=f".{destination.stem}-",
        suffix=".tmp.parquet",
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
        default="data/processed/unsw_nb15_cleaned.parquet",
        help="Parquet limpo e não escalado.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/unsw_nb15_temporal_sorted.parquet",
        help="Novo parquet ordenado; o arquivo original não será alterado.",
    )
    parser.add_argument(
        "--report",
        default="reports_local/prospective/unsw_temporal_sort.json",
        help="Relatório JSON da transformação.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Substitui explicitamente uma saída já existente.",
    )
    args = parser.parse_args()

    report = sort_unsw_temporal_parquet(
        args.input,
        args.output,
        args.report,
        overwrite=args.overwrite,
    )
    print(f"Parquet temporal salvo em: {args.output}")
    print(f"Relatório salvo em: {args.report}")
    print(f"Linhas preservadas: {report['output']['rows']}")
    print(
        "Regressões temporais: "
        f"{report['input']['backward_transitions_before']} → "
        f"{report['output']['backward_transitions_after']}"
    )
    print(f"Próximo passo: {report['next_step']}")


if __name__ == "__main__":
    main()
