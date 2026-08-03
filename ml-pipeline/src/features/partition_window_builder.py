"""Janelas auditáveis criadas separadamente por partição e sessão.

O módulo materializa os índices das janelas de treino e validação sem duplicar
as 204 features antes da seleção de atributos. Para o treinamento, expõe um
iterador que realiza as janelas 3D em lotes depois que as colunas selecionadas
forem conhecidas. O teste temporal não é recebido como entrada nesta etapa.

Uso::

    python -m src.features.partition_window_builder
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any, Iterator, Sequence

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


DEFAULT_INPUT_DIR = Path("data/processed/unsw_nb15_temporal_preprocessed")
DEFAULT_OUTPUT_DIR = Path("data/processed/unsw_nb15_temporal_windows")
DEFAULT_REPORT_PATH = Path("reports_temporal/unsw/windows/window_audit.json")
DEFAULT_WINDOW_SIZE = 10
SPLITS = ("train", "validation")
REQUIRED_METADATA_COLUMNS = {
    "record_id",
    "temporal_session",
    "split",
    "Binary_Label",
    "attack_cat",
    "Stime",
    "Ltime",
    "source_file",
}
NON_FEATURE_COLUMNS = REQUIRED_METADATA_COLUMNS


@dataclass(frozen=True)
class PartitionWindowBatch:
    """Um lote de janelas sequenciais com rastreabilidade integral."""

    X: np.ndarray
    y: np.ndarray
    attack_types: np.ndarray
    window_record_ids: np.ndarray
    target_record_ids: np.ndarray
    temporal_sessions: np.ndarray
    temporal_blocks: np.ndarray
    source_files: np.ndarray

    def flatten(self) -> np.ndarray:
        """Retorna as mesmas janelas em formato tabular para RF e DT."""
        return self.X.reshape(self.X.shape[0], -1)


def create_partition_window_manifest(
    frame: pd.DataFrame,
    *,
    window_size: int = DEFAULT_WINDOW_SIZE,
    expected_split: str | None = None,
    boundary_columns: Sequence[str] = (),
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Cria uma linha de manifesto para cada janela válida de uma partição."""
    _validate_partition_frame(
        frame,
        window_size=window_size,
        expected_split=expected_split,
        boundary_columns=boundary_columns,
    )
    record_columns = [f"record_id_t{offset:02d}" for offset in range(window_size)]
    manifests: list[pd.DataFrame] = []
    block_summaries: list[dict[str, Any]] = []

    for block_id, session_id, source_file, block in _iter_contiguous_blocks(
        frame, boundary_columns=boundary_columns
    ):
        rows = len(block)
        windows = max(0, rows - window_size + 1)
        block_summaries.append(
            {
                "temporal_block": int(block_id),
                "temporal_session": int(session_id),
                "source_file": str(source_file),
                "rows": int(rows),
                "windows": int(windows),
            }
        )
        if windows == 0:
            continue

        record_ids = block["record_id"].to_numpy(dtype=np.int64)
        window_ids = np.lib.stride_tricks.sliding_window_view(
            record_ids, window_size
        )
        endpoints = np.arange(window_size - 1, rows)
        starts = endpoints - window_size + 1
        data: dict[str, Any] = {
            column: window_ids[:, offset]
            for offset, column in enumerate(record_columns)
        }
        data.update(
            {
                "split": block["split"].iloc[endpoints].astype(str).to_numpy(),
                "temporal_session": np.full(windows, int(session_id), dtype=np.int32),
                "temporal_block": np.full(windows, int(block_id), dtype=np.int32),
                "target_record_id": record_ids[endpoints],
                "Binary_Label": block["Binary_Label"].iloc[endpoints].to_numpy(
                    dtype=np.int8
                ),
                "attack_cat": block["attack_cat"].iloc[endpoints].astype(str).to_numpy(),
                "window_start_stime": block["Stime"].iloc[starts].to_numpy(
                    dtype=np.int64
                ),
                "window_end_ltime": block["Ltime"].iloc[endpoints].to_numpy(
                    dtype=np.int64
                ),
                "target_source_file": np.full(windows, str(source_file), dtype=object),
            }
        )
        for boundary_column in boundary_columns:
            data[boundary_column] = block[boundary_column].iloc[endpoints].to_numpy()
        manifests.append(pd.DataFrame(data))

    if not manifests:
        raise ValueError(
            f"Nenhuma sessão possui ao menos window_size={window_size} registros."
        )
    manifest = pd.concat(manifests, ignore_index=True)
    manifest.insert(0, "window_id", np.arange(len(manifest), dtype=np.int64))
    _validate_manifest(manifest, window_size=window_size)
    return manifest, block_summaries


def iter_partition_window_batches(
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    *,
    window_size: int = DEFAULT_WINDOW_SIZE,
    batch_size: int = 25_000,
    expected_split: str | None = None,
    boundary_columns: Sequence[str] = (),
) -> Iterator[PartitionWindowBatch]:
    """Realiza janelas 3D em lotes, sempre dentro de uma única sessão."""
    if batch_size < 1:
        raise ValueError("batch_size deve ser positivo.")
    _validate_partition_frame(
        frame,
        window_size=window_size,
        expected_split=expected_split,
        boundary_columns=boundary_columns,
    )
    names = list(feature_columns)
    if not names:
        raise ValueError("feature_columns não pode ser vazio.")
    if len(names) != len(set(names)):
        raise ValueError("feature_columns não pode conter duplicatas.")
    missing = sorted(set(names).difference(frame.columns))
    if missing:
        raise ValueError(f"Features ausentes: {missing}")
    forbidden = sorted(set(names).intersection(NON_FEATURE_COLUMNS))
    if forbidden:
        raise ValueError(f"Metadados não podem ser usados como features: {forbidden}")

    for block_id, session_id, source_file, session in _iter_contiguous_blocks(
        frame, boundary_columns=boundary_columns
    ):
        n_windows = len(session) - window_size + 1
        if n_windows <= 0:
            continue
        features = session[names].to_numpy(dtype=np.float32)
        labels = session["Binary_Label"].to_numpy(dtype=np.int8)
        attacks = session["attack_cat"].astype(str).to_numpy()
        record_ids = session["record_id"].to_numpy(dtype=np.int64)
        for first_window in range(0, n_windows, batch_size):
            last_window = min(first_window + batch_size, n_windows)
            row_stop = last_window + window_size - 1
            feature_rows = features[first_window:row_stop]
            id_rows = record_ids[first_window:row_stop]
            X = np.moveaxis(
                np.lib.stride_tricks.sliding_window_view(
                    feature_rows, window_shape=window_size, axis=0
                ),
                -1,
                1,
            ).copy()
            window_record_ids = np.lib.stride_tricks.sliding_window_view(
                id_rows, window_size
            ).copy()
            endpoints = np.arange(
                first_window + window_size - 1,
                last_window + window_size - 1,
            )
            yield PartitionWindowBatch(
                X=X,
                y=labels[endpoints].copy(),
                attack_types=attacks[endpoints].copy(),
                window_record_ids=window_record_ids,
                target_record_ids=record_ids[endpoints].copy(),
                temporal_sessions=np.full(
                    len(endpoints), int(session_id), dtype=np.int32
                ),
                temporal_blocks=np.full(
                    len(endpoints), int(block_id), dtype=np.int32
                ),
                source_files=np.full(len(endpoints), str(source_file), dtype=object),
            )


def materialize_train_validation_window_manifests(
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    *,
    window_size: int = DEFAULT_WINDOW_SIZE,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Materializa índices de janelas apenas para treino e validação."""
    _validate_window_size(window_size)
    source_dir = Path(input_dir)
    destination_dir = Path(output_dir)
    report = Path(report_path)
    inputs = {split: source_dir / f"{split}.parquet" for split in SPLITS}
    outputs = {
        split: destination_dir / f"{split}_window_index.parquet" for split in SPLITS
    }
    missing = [str(path) for path in inputs.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Partições não encontradas: " + ", ".join(missing))
    targets = [*outputs.values(), report]
    existing = [str(path) for path in targets if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Saídas já existem; a geração não sobrescreve por padrão: "
            + ", ".join(existing)
        )

    hashes_before = {split: _file_sha256(path) for split, path in inputs.items()}
    metadata_columns = sorted(REQUIRED_METADATA_COLUMNS)
    manifests: dict[str, pd.DataFrame] = {}
    block_summaries: dict[str, list[dict[str, Any]]] = {}
    input_schemas: dict[str, list[str]] = {}
    for split in SPLITS:
        schema_names = pq.read_schema(inputs[split]).names
        input_schemas[split] = schema_names
        available_metadata = [
            column for column in metadata_columns if column in schema_names
        ]
        raw_metadata = pd.read_parquet(inputs[split], columns=available_metadata)
        manifests[split], block_summaries[split] = (
            create_partition_window_manifest(
                raw_metadata,
                window_size=window_size,
                expected_split=split,
            )
        )

    overlap = np.intersect1d(
        _unique_manifest_record_ids(manifests["train"], window_size),
        _unique_manifest_record_ids(manifests["validation"], window_size),
    )
    if overlap.size:
        raise ValueError(
            f"Treino e validação compartilham {overlap.size} record_id nas janelas."
        )

    destination_dir.mkdir(parents=True, exist_ok=True)
    for split in SPLITS:
        _atomic_write_parquet(manifests[split], outputs[split])
    hashes_after = {split: _file_sha256(path) for split, path in inputs.items()}
    if hashes_before != hashes_after:
        raise RuntimeError("Uma partição de entrada mudou durante a geração.")

    output_audits = {
        split: _output_audit(
            manifests[split],
            outputs[split],
            block_summaries[split],
            window_size=window_size,
            input_feature_count=len(
                [
                    name
                    for name in input_schemas[split]
                    if name not in NON_FEATURE_COLUMNS
                ]
            ),
        )
        for split in SPLITS
    }
    del manifests

    test_output = destination_dir / "test_window_index.parquet"
    payload = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "partition_session_and_source_isolated_sliding_windows",
        "window_size": int(window_size),
        "target_rule": "Binary_Label e attack_cat do último registro da janela.",
        "inputs": {
            split: {
                "path": str(path),
                "sha256_before": hashes_before[split],
                "sha256_after": hashes_after[split],
            }
            for split, path in inputs.items()
        },
        "outputs": output_audits,
        "feature_materialization": {
            "index_manifests_materialized": True,
            "feature_cubes_materialized_before_selection": False,
            "reason": (
                "A seleção de atributos precede a criação das features 3D; "
                "iter_partition_window_batches realiza as janelas selecionadas em lotes."
            ),
            "iterator": "src.features.partition_window_builder.iter_partition_window_batches",
        },
        "cross_partition_integrity": {
            "train_validation_shared_record_ids": int(overlap.size),
            "record_ids_disjoint": overlap.size == 0,
        },
        "test_policy": {
            "status": "closed",
            "test_input_was_not_loaded": True,
            "test_window_output": str(test_output),
            "test_window_output_exists": test_output.exists(),
        },
        "acceptance": {
            "inputs_unchanged": hashes_before == hashes_after,
            "windows_created_separately_by_partition": True,
            "windows_created_separately_by_session": all(
                item["all_windows_within_one_session"]
                for item in output_audits.values()
            ),
            "windows_created_separately_by_source_file": all(
                item["all_windows_within_one_source_file"]
                for item in output_audits.values()
            ),
            "target_is_last_record": all(
                item["target_is_last_record"] for item in output_audits.values()
            ),
            "record_ids_disjoint_between_train_validation": overlap.size == 0,
            "test_remained_closed": not test_output.exists(),
        },
    }
    _atomic_write_json(payload, report)
    return payload


def _validate_partition_frame(
    frame: pd.DataFrame,
    *,
    window_size: int,
    expected_split: str | None,
    boundary_columns: Sequence[str] = (),
) -> None:
    _validate_window_size(window_size)
    missing = sorted(REQUIRED_METADATA_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Metadados obrigatórios ausentes: {missing}")
    if frame.empty:
        raise ValueError("A partição não pode estar vazia.")
    missing_boundaries = sorted(set(boundary_columns).difference(frame.columns))
    if missing_boundaries:
        raise ValueError(f"Colunas de fronteira ausentes: {missing_boundaries}")
    if not frame["record_id"].is_unique:
        raise ValueError("record_id deve ser único dentro da partição.")
    split_values = sorted(frame["split"].dropna().astype(str).unique().tolist())
    if len(split_values) != 1:
        raise ValueError(f"A entrada deve conter uma só partição: {split_values}")
    if expected_split is not None and split_values != [expected_split]:
        raise ValueError(
            f"Partição esperada {expected_split}, recebida {split_values}."
        )
    sessions = frame["temporal_session"].to_numpy()
    session_runs = 1 + int(np.count_nonzero(sessions[1:] != sessions[:-1]))
    if session_runs != frame["temporal_session"].nunique():
        raise ValueError("Cada temporal_session deve ocupar um bloco contíguo.")
    for session_id, session in frame.groupby(
        "temporal_session", sort=False, observed=True
    ):
        if not session["Stime"].is_monotonic_increasing:
            raise ValueError(f"Stime não está ordenado na sessão {session_id}.")


def _iter_contiguous_blocks(
    frame: pd.DataFrame,
    *,
    boundary_columns: Sequence[str] = (),
) -> Iterator[tuple[int, int, str, pd.DataFrame]]:
    """Separa toda troca de sessão ou arquivo, inclusive arquivos intercalados."""
    change = (
        frame["temporal_session"].ne(frame["temporal_session"].shift())
        | frame["source_file"].astype(str).ne(
            frame["source_file"].astype(str).shift()
        )
    )
    for boundary_column in boundary_columns:
        change |= frame[boundary_column].ne(frame[boundary_column].shift())
    block_ids = change.cumsum().to_numpy(dtype=np.int32) - 1
    for block_id in np.unique(block_ids):
        block = frame.iloc[np.flatnonzero(block_ids == block_id)]
        yield (
            int(block_id),
            int(block["temporal_session"].iloc[0]),
            str(block["source_file"].iloc[0]),
            block,
        )


def _validate_manifest(manifest: pd.DataFrame, *, window_size: int) -> None:
    record_columns = [f"record_id_t{offset:02d}" for offset in range(window_size)]
    if not manifest["window_id"].is_unique:
        raise RuntimeError("window_id duplicado no manifesto.")
    if not np.array_equal(
        manifest["target_record_id"].to_numpy(),
        manifest[record_columns[-1]].to_numpy(),
    ):
        raise RuntimeError("O alvo não corresponde ao último registro da janela.")
    if (manifest[record_columns].nunique(axis=1) != window_size).any():
        raise RuntimeError("Uma janela contém record_id repetido.")


def _validate_window_size(window_size: int) -> None:
    if not isinstance(window_size, int) or isinstance(window_size, bool) or window_size < 2:
        raise ValueError("window_size deve ser um inteiro maior ou igual a 2.")


def _unique_manifest_record_ids(
    manifest: pd.DataFrame, window_size: int
) -> np.ndarray:
    columns = [f"record_id_t{offset:02d}" for offset in range(window_size)]
    return np.unique(manifest[columns].to_numpy(dtype=np.int64))


def _output_audit(
    manifest: pd.DataFrame,
    path: Path,
    blocks: list[dict[str, Any]],
    *,
    window_size: int,
    input_feature_count: int,
) -> dict[str, Any]:
    record_columns = [f"record_id_t{offset:02d}" for offset in range(window_size)]
    unique_ids = np.unique(manifest[record_columns].to_numpy(dtype=np.int64))
    input_rows = sum(int(block["rows"]) for block in blocks)
    return {
        "path": str(path),
        "sha256": _file_sha256(path),
        "size_bytes": path.stat().st_size,
        "windows": int(len(manifest)),
        "columns": int(len(manifest.columns)),
        "input_feature_count": int(input_feature_count),
        "input_rows": input_rows,
        "unique_record_ids_used": int(len(unique_ids)),
        "rows_not_used_in_any_window": int(input_rows - len(unique_ids)),
        "blocks_too_short_for_a_window": sum(
            int(block["windows"] == 0) for block in blocks
        ),
        "unique_record_ids_sha256": _record_ids_sha256(unique_ids),
        "window_record_id_columns": record_columns,
        "blocks": blocks,
        "all_windows_within_one_session": True,
        "all_windows_within_one_source_file": True,
        "target_is_last_record": bool(
            np.array_equal(
                manifest["target_record_id"].to_numpy(),
                manifest[record_columns[-1]].to_numpy(),
            )
        ),
        "both_target_classes_present": manifest["Binary_Label"].nunique() == 2,
    }


def _record_ids_sha256(record_ids: np.ndarray) -> str:
    return sha256(np.asarray(record_ids, dtype="<i8").tobytes()).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_parquet(frame: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        frame.to_parquet(temporary, index=False)
        check = pq.ParquetFile(temporary)
        if check.metadata.num_rows != len(frame):
            raise RuntimeError(f"Contagem divergente no Parquet temporário: {destination}")
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--window-size", type=int, default=DEFAULT_WINDOW_SIZE)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    payload = materialize_train_validation_window_manifests(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        report_path=args.report_path,
        window_size=args.window_size,
        overwrite=args.overwrite,
    )
    print(json.dumps(payload["acceptance"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
