"""Partições temporais auditáveis para a tarefa de detecção do UNSW-NB15.

O módulo parte do dataset limpo e não escalonado, atribui ``record_id`` antes
da ordenação, identifica sessões separadas por grandes lacunas temporais e
materializa treino, validação e teste sem embaralhamento. Nenhuma transformação
estatística ou seleção de atributos é executada nesta etapa.

Uso:
    python -m src.data.detection_temporal_splitter
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


DEFAULT_INPUT_PATH = Path("data/processed/unsw_nb15_cleaned_temporal.parquet")
DEFAULT_OUTPUT_DIR = Path("data/processed/unsw_nb15_temporal")
DEFAULT_REPORT_PATH = Path("reports_temporal/unsw/split_audit.json")
DEFAULT_SESSION_GAP_SECONDS = 3600
DEFAULT_WINDOW_SIZE = 10
SPLIT_ORDER = ("train", "validation", "test")
REQUIRED_COLUMNS = {
    "Stime",
    "Ltime",
    "source_file",
    "Binary_Label",
    "attack_cat",
}
METADATA_COLUMNS = {"record_id", "temporal_session", "split"}


class DetectionTemporalSplitError(RuntimeError):
    """Indica que o dataset não atende ao protocolo temporal esperado."""


def assign_record_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Atribui identificadores estáveis pela posição no arquivo limpo."""
    if "record_id" in df.columns:
        raise ValueError("A entrada já contém record_id; a origem deve ser imutável.")
    result = df.copy()
    result.insert(0, "record_id", np.arange(len(result), dtype=np.int64))
    return result


def stable_temporal_sort(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena fluxos sem perder o identificador da posição original."""
    _validate_required_columns(df)
    if "record_id" not in df.columns:
        raise ValueError("Atribua record_id antes da ordenação temporal.")
    result = df.sort_values(
        ["Stime", "Ltime", "source_file", "record_id"],
        kind="stable",
    ).reset_index(drop=True)
    if (np.diff(result["Stime"].to_numpy(dtype=np.int64)) < 0).any():
        raise DetectionTemporalSplitError("A ordenação ainda contém regressões de Stime.")
    return result


def identify_natural_sessions(
    sorted_df: pd.DataFrame,
    *,
    gap_seconds: int = DEFAULT_SESSION_GAP_SECONDS,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Separa sessões quando a lacuna entre timestamps supera o limiar."""
    if gap_seconds < 1:
        raise ValueError("gap_seconds deve ser positivo.")
    if sorted_df.empty:
        raise ValueError("O dataset temporal não pode estar vazio.")
    times = sorted_df["Stime"].to_numpy(dtype=np.int64)
    if (np.diff(times) < 0).any():
        raise ValueError("O dataset deve estar ordenado antes de identificar sessões.")
    unique_times = np.unique(times)
    cuts = unique_times[1:][np.diff(unique_times) > gap_seconds]
    result = sorted_df.copy()
    result["temporal_session"] = np.searchsorted(cuts, times, side="right").astype(
        np.int16
    )
    _validate_session_boundaries(result)
    return result, cuts.astype(np.int64)


def assign_splits_and_purge(
    session_df: pd.DataFrame,
    *,
    window_size: int = DEFAULT_WINDOW_SIZE,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """Reserva as duas últimas sessões e purga fronteiras adjacentes."""
    if window_size < 1:
        raise ValueError("window_size deve ser maior ou igual a 1.")
    sessions = sorted(session_df["temporal_session"].unique().tolist())
    if len(sessions) < 3:
        raise DetectionTemporalSplitError(
            "São necessárias ao menos três sessões para treino, validação e teste."
        )
    validation_session = sessions[-2]
    test_session = sessions[-1]
    split_values = np.full(len(session_df), "train", dtype=object)
    split_values[
        session_df["temporal_session"].to_numpy() == validation_session
    ] = "validation"
    split_values[session_df["temporal_session"].to_numpy() == test_session] = "test"
    assigned = session_df.copy()
    assigned["split"] = split_values

    purge_per_side = window_size - 1
    keep = np.ones(len(assigned), dtype=bool)
    purge_events: list[dict[str, Any]] = []
    for left_session, right_session in zip(sessions[:-1], sessions[1:]):
        left_positions = np.flatnonzero(
            assigned["temporal_session"].to_numpy() == left_session
        )
        right_positions = np.flatnonzero(
            assigned["temporal_session"].to_numpy() == right_session
        )
        if purge_per_side and (
            len(left_positions) <= purge_per_side
            or len(right_positions) <= purge_per_side
        ):
            raise DetectionTemporalSplitError(
                "Uma sessão é pequena demais para a purga configurada."
            )
        left_purged = left_positions[-purge_per_side:] if purge_per_side else np.array([], dtype=int)
        right_purged = right_positions[:purge_per_side] if purge_per_side else np.array([], dtype=int)
        keep[left_purged] = False
        keep[right_purged] = False
        left_end_ltime = int(assigned.iloc[left_positions]["Ltime"].max())
        right_start_stime = int(assigned.iloc[right_positions]["Stime"].min())
        purge_events.append(
            {
                "left_session": int(left_session),
                "right_session": int(right_session),
                "left_split": str(assigned.iloc[left_positions[0]]["split"]),
                "right_split": str(assigned.iloc[right_positions[0]]["split"]),
                "natural_gap_seconds": right_start_stime - left_end_ltime,
                "purged_left_rows": int(len(left_purged)),
                "purged_right_rows": int(len(right_purged)),
                "purged_left_record_ids_sha256": _record_ids_sha256(
                    assigned.iloc[left_purged]["record_id"].to_numpy(dtype=np.int64)
                ),
                "purged_right_record_ids_sha256": _record_ids_sha256(
                    assigned.iloc[right_purged]["record_id"].to_numpy(dtype=np.int64)
                ),
            }
        )

    purged = assigned.loc[~keep].copy()
    retained = assigned.loc[keep].copy()
    partitions = {
        split: retained.loc[retained["split"].eq(split)].reset_index(drop=True)
        for split in SPLIT_ORDER
    }
    _validate_partitions(partitions, window_size=window_size)
    audit = {
        "window_size": int(window_size),
        "purge_per_boundary_side_rows": int(purge_per_side),
        "purged_rows_total": int(len(purged)),
        "purged_record_ids_sha256": _record_ids_sha256(
            purged["record_id"].to_numpy(dtype=np.int64)
        ),
        "events": purge_events,
    }
    return partitions, audit


def window_integrity_summary(
    partitions: dict[str, pd.DataFrame],
    *,
    window_size: int = DEFAULT_WINDOW_SIZE,
) -> dict[str, Any]:
    """Prova que janelas internas às sessões não compartilham registros."""
    record_ids: dict[str, np.ndarray] = {}
    partition_summaries: dict[str, Any] = {}
    for split in SPLIT_ORDER:
        part = partitions[split]
        record_ids[split] = np.sort(part["record_id"].to_numpy(dtype=np.int64))
        sessions: list[dict[str, int]] = []
        total_windows = 0
        for session_id, group in part.groupby("temporal_session", sort=True):
            count = max(0, len(group) - window_size + 1)
            total_windows += count
            sessions.append(
                {
                    "temporal_session": int(session_id),
                    "rows": int(len(group)),
                    "windows": int(count),
                }
            )
        partition_summaries[split] = {
            "rows": int(len(part)),
            "windows_created_separately_by_session": int(total_windows),
            "sessions": sessions,
            "record_ids_sha256": _record_ids_sha256(record_ids[split]),
        }

    overlaps = {
        "train_validation": int(
            np.intersect1d(record_ids["train"], record_ids["validation"]).size
        ),
        "train_test": int(
            np.intersect1d(record_ids["train"], record_ids["test"]).size
        ),
        "validation_test": int(
            np.intersect1d(record_ids["validation"], record_ids["test"]).size
        ),
    }
    return {
        "window_rule": "Criar janelas separadamente dentro de cada temporal_session.",
        "partitions": partition_summaries,
        "record_id_overlaps": overlaps,
        "all_partition_record_ids_disjoint": all(value == 0 for value in overlaps.values()),
        "windows_can_cross_session": False,
    }


def materialize_detection_temporal_split(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    *,
    session_gap_seconds: int = DEFAULT_SESSION_GAP_SECONDS,
    window_size: int = DEFAULT_WINDOW_SIZE,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Gera partições Parquet e relatório completo de integridade."""
    source = Path(input_path)
    destination = Path(output_dir)
    report = Path(report_path)
    if not source.exists():
        raise FileNotFoundError(f"Dataset limpo não encontrado: {source}")
    outputs = {split: destination / f"{split}.parquet" for split in SPLIT_ORDER}
    targets = [*outputs.values(), report]
    existing = [path for path in targets if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Saídas já existem; a geração não sobrescreve por padrão: "
            + ", ".join(str(path) for path in existing)
        )
    if source.resolve() in {path.resolve() for path in targets}:
        raise ValueError("O arquivo de entrada não pode ser usado como saída.")

    source_hash_before = _file_sha256(source)
    df = pd.read_parquet(source)
    _validate_required_columns(df)
    regressions_before = int(
        (np.diff(df["Stime"].to_numpy(dtype=np.int64)) < 0).sum()
    )
    identified = assign_record_ids(df)
    sorted_df = stable_temporal_sort(identified)
    session_df, cut_times = identify_natural_sessions(
        sorted_df,
        gap_seconds=session_gap_seconds,
    )
    partitions, purge_audit = assign_splits_and_purge(
        session_df,
        window_size=window_size,
    )
    integrity = window_integrity_summary(partitions, window_size=window_size)

    destination.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    for split, path in outputs.items():
        _atomic_write_parquet(partitions[split], path)

    source_hash_after = _file_sha256(source)
    if source_hash_before != source_hash_after:
        raise RuntimeError("O hash do dataset de entrada mudou durante a geração.")

    session_summary = _session_summary(session_df)
    partition_summary = {
        split: _partition_summary(partitions[split], outputs[split])
        for split in SPLIT_ORDER
    }
    payload = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "natural_session_chronological_holdout",
        "shuffle": False,
        "input": {
            "path": str(source),
            "size_bytes": source.stat().st_size,
            "sha256_before": source_hash_before,
            "sha256_after": source_hash_after,
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
        },
        "record_id": {
            "dtype": "int64",
            "assignment": "Posição zero-based no Parquet limpo antes da ordenação.",
            "unique": bool(session_df["record_id"].is_unique),
            "minimum": int(session_df["record_id"].min()),
            "maximum": int(session_df["record_id"].max()),
        },
        "sorting": {
            "keys": ["Stime", "Ltime", "source_file", "record_id"],
            "kind": "stable",
            "stime_regressions_before": regressions_before,
            "stime_regressions_after": int(
                (np.diff(session_df["Stime"].to_numpy(dtype=np.int64)) < 0).sum()
            ),
        },
        "sessions": {
            "gap_threshold_seconds": int(session_gap_seconds),
            "cut_stimes": cut_times.astype(int).tolist(),
            "count": int(session_df["temporal_session"].nunique()),
            "items": session_summary,
        },
        "purge": purge_audit,
        "partitions": partition_summary,
        "window_integrity": integrity,
        "test_policy": {
            "status": "closed_after_materialization",
            "allowed_use": "Uma única avaliação após congelar pré-processamento, seleção e hiperparâmetros na validação.",
        },
        "acceptance": {
            "source_unchanged": True,
            "record_ids_unique": bool(session_df["record_id"].is_unique),
            "chronological_order": True,
            "both_classes_in_every_partition": all(
                part["Binary_Label"].nunique() == 2 for part in partitions.values()
            ),
            "all_attack_types_in_every_partition": all(
                part.loc[part["Binary_Label"].eq(1), "attack_cat"].nunique() == 9
                for part in partitions.values()
            ),
            "record_ids_disjoint": integrity["all_partition_record_ids_disjoint"],
            "windows_cross_sessions": False,
        },
    }
    _atomic_write_json(payload, report)
    return payload


def _session_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    last_session = int(df["temporal_session"].max())
    for session_id, group in df.groupby("temporal_session", sort=True):
        split = "train"
        if int(session_id) == last_session - 1:
            split = "validation"
        elif int(session_id) == last_session:
            split = "test"
        summaries.append(
            {
                "temporal_session": int(session_id),
                "assigned_split": split,
                "rows_before_purge": int(len(group)),
                "start_stime": int(group["Stime"].min()),
                "end_ltime": int(group["Ltime"].max()),
                "benign_before_purge": int(group["Binary_Label"].eq(0).sum()),
                "attacks_before_purge": int(group["Binary_Label"].eq(1).sum()),
                "attack_types_before_purge": sorted(
                    group.loc[group["Binary_Label"].eq(1), "attack_cat"]
                    .astype(str)
                    .unique()
                    .tolist()
                ),
            }
        )
    return summaries


def _partition_summary(df: pd.DataFrame, path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": _file_sha256(path),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "all_columns_and_row_groups_readable": _parquet_all_columns_readable(path),
        "start_stime": int(df["Stime"].min()),
        "end_ltime": int(df["Ltime"].max()),
        "benign": int(df["Binary_Label"].eq(0).sum()),
        "attacks": int(df["Binary_Label"].eq(1).sum()),
        "attack_types": sorted(
            df.loc[df["Binary_Label"].eq(1), "attack_cat"].astype(str).unique().tolist()
        ),
        "temporal_sessions": sorted(df["temporal_session"].astype(int).unique().tolist()),
        "record_ids_sha256": _record_ids_sha256(
            np.sort(df["record_id"].to_numpy(dtype=np.int64))
        ),
    }


def _validate_required_columns(df: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(f"Colunas temporais obrigatórias ausentes: {missing}")
    if df.empty:
        raise ValueError("O dataset temporal não pode estar vazio.")
    if df[["Stime", "Ltime"]].isna().any().any():
        raise ValueError("Stime e Ltime não podem conter valores ausentes.")
    if (df["Ltime"] < df["Stime"]).any():
        raise DetectionTemporalSplitError("Foram encontradas durações negativas.")


def _validate_session_boundaries(df: pd.DataFrame) -> None:
    sessions = sorted(df["temporal_session"].unique().tolist())
    for left_session, right_session in zip(sessions[:-1], sessions[1:]):
        left_end = int(
            df.loc[df["temporal_session"].eq(left_session), "Ltime"].max()
        )
        right_start = int(
            df.loc[df["temporal_session"].eq(right_session), "Stime"].min()
        )
        if left_end >= right_start:
            raise DetectionTemporalSplitError(
                "Fluxos atravessam a fronteira entre sessões temporais."
            )


def _validate_partitions(
    partitions: dict[str, pd.DataFrame],
    *,
    window_size: int,
) -> None:
    for split in SPLIT_ORDER:
        part = partitions.get(split)
        if part is None or part.empty:
            raise DetectionTemporalSplitError(f"Partição vazia: {split}.")
        if len(part) < window_size:
            raise DetectionTemporalSplitError(
                f"Partição {split} menor que window_size={window_size}."
            )
        if part["Binary_Label"].nunique() != 2:
            raise DetectionTemporalSplitError(
                f"Partição {split} não contém ambas as classes."
            )
    ordered = [partitions[split] for split in SPLIT_ORDER]
    for left, right in zip(ordered[:-1], ordered[1:]):
        if int(left["Ltime"].max()) >= int(right["Stime"].min()):
            raise DetectionTemporalSplitError(
                "As partições não preservam separação cronológica."
            )


def _record_ids_sha256(record_ids: np.ndarray) -> str:
    normalized = np.asarray(record_ids, dtype="<i8")
    return sha256(normalized.tobytes()).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_parquet(df: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        df.to_parquet(temporary, index=False)
        if not _parquet_all_columns_readable(temporary):
            raise RuntimeError(
                f"Falha de leitura ao validar Parquet temporário: {temporary}"
            )
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_json(payload: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    try:
        json.loads(temporary.read_text(encoding="utf-8"))
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _parquet_all_columns_readable(path: Path) -> bool:
    parquet = pq.ParquetFile(path)
    for row_group in range(parquet.num_row_groups):
        for column in parquet.schema_arrow.names:
            try:
                parquet.read_row_group(row_group, columns=[column])
            except (OSError, ValueError):
                return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-path", default=str(DEFAULT_INPUT_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument(
        "--session-gap-seconds",
        type=int,
        default=DEFAULT_SESSION_GAP_SECONDS,
    )
    parser.add_argument("--window-size", type=int, default=DEFAULT_WINDOW_SIZE)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    payload = materialize_detection_temporal_split(
        input_path=args.input_path,
        output_dir=args.output_dir,
        report_path=args.report_path,
        session_gap_seconds=args.session_gap_seconds,
        window_size=args.window_size,
        overwrite=args.overwrite,
    )
    print(json.dumps(payload["acceptance"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
