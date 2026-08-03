"""Folds temporais expansivos e purgados para o desenvolvimento da detecção.

Cria quatro blocos cronológicos no conjunto de desenvolvimento e três folds:

* fold 1: bloco 0 -> bloco 1;
* fold 2: blocos 0-1 -> bloco 2;
* fold 3: blocos 0-2 -> bloco 3 (todo o futuro restante).

As fronteiras são definidas no período ativo de ataques do treino para evitar
folds de validação com uma única classe. Nove registros de cada lado de cada
fronteira são purgados para a janela principal de dez registros. O teste
temporal fechado não é recebido como entrada.

Uso::

    python -m src.data.expanding_temporal_folds
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

from src.features.partition_window_builder import create_partition_window_manifest


DEFAULT_INPUT_DIR = Path("data/processed/unsw_nb15_temporal")
DEFAULT_OUTPUT_DIR = Path("data/processed/unsw_nb15_temporal_folds")
DEFAULT_REPORT_PATH = Path("reports_temporal/unsw/folds/expanding_folds_audit.json")
DEFAULT_N_FOLDS = 3
DEFAULT_WINDOW_SIZE = 10
REQUIRED_COLUMNS = {
    "record_id",
    "Stime",
    "Ltime",
    "source_file",
    "Binary_Label",
    "attack_cat",
    "temporal_session",
    "split",
}


def create_expanding_fold_assignments(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    *,
    n_folds: int = DEFAULT_N_FOLDS,
    window_size: int = DEFAULT_WINDOW_SIZE,
) -> tuple[list[dict[str, pd.DataFrame]], dict[str, Any]]:
    """Define folds expansivos sobre metadados temporais já particionados."""
    if n_folds < 2:
        raise ValueError("n_folds deve ser maior ou igual a 2.")
    if window_size < 2:
        raise ValueError("window_size deve ser maior ou igual a 2.")
    _validate_input_partition(train, expected_split="train")
    _validate_input_partition(validation, expected_split="validation")
    if np.intersect1d(train["record_id"], validation["record_id"]).size:
        raise ValueError("Treino e validação de entrada compartilham record_id.")
    if int(train["Ltime"].max()) >= int(validation["Stime"].min()):
        raise ValueError("Treino e validação não estão cronologicamente separados.")

    train = train.reset_index(drop=True).copy()
    validation = validation.reset_index(drop=True).copy()
    train["development_origin_split"] = "train"
    validation["development_origin_split"] = "validation"
    development = pd.concat([train, validation], ignore_index=True)

    attack_positions = np.flatnonzero(train["Binary_Label"].to_numpy() == 1)
    if attack_positions.size == 0:
        raise ValueError("O treino precisa conter ataques para criar folds válidos.")
    active_attack_stop = int(attack_positions[-1]) + 1
    boundary_positions = _attack_active_boundaries(
        train,
        active_attack_stop=active_attack_stop,
        n_folds=n_folds,
    )
    positions = np.arange(len(development))
    development["development_block"] = np.searchsorted(
        np.asarray(boundary_positions), positions, side="right"
    ).astype(np.int16)

    purge_per_side = window_size - 1
    keep = np.ones(len(development), dtype=bool)
    purge_events: list[dict[str, Any]] = []
    for boundary_index, boundary_position in enumerate(boundary_positions, start=1):
        left = np.arange(boundary_position - purge_per_side, boundary_position)
        minimum_right_end = boundary_position + purge_per_side
        if left.min() < 0 or minimum_right_end > len(development):
            raise ValueError("Uma fronteira não comporta a purga configurada.")
        left_retained_end = boundary_position - purge_per_side
        left_max_ltime = int(development.iloc[:left_retained_end]["Ltime"].max())
        temporal_right_end = int(
            np.searchsorted(
                development["Stime"].to_numpy(dtype=np.int64),
                left_max_ltime,
                side="right",
            )
        )
        right_end = max(minimum_right_end, temporal_right_end)
        if right_end >= len(development):
            raise ValueError("O embargo temporal consumiria todo o futuro disponível.")
        right = np.arange(boundary_position, right_end)
        keep[left] = False
        keep[right] = False
        purge_events.append(
            {
                "boundary": boundary_index,
                "left_block": boundary_index - 1,
                "right_block": boundary_index,
                "left_last_stime_before_purge": int(
                    development.iloc[boundary_position - 1]["Stime"]
                ),
                "right_first_stime_before_purge": int(
                    development.iloc[boundary_position]["Stime"]
                ),
                "purged_left_rows": int(len(left)),
                "purged_right_rows": int(len(right)),
                "minimum_purge_each_side_rows": int(purge_per_side),
                "additional_right_rows_for_temporal_embargo": int(
                    len(right) - purge_per_side
                ),
                "left_max_ltime_after_left_purge": left_max_ltime,
                "right_first_stime_after_embargo": int(
                    development.iloc[right_end]["Stime"]
                ),
                "purged_left_record_ids_sha256": _record_ids_sha256(
                    development.iloc[left]["record_id"].to_numpy(dtype=np.int64)
                ),
                "purged_right_record_ids_sha256": _record_ids_sha256(
                    development.iloc[right]["record_id"].to_numpy(dtype=np.int64)
                ),
            }
        )

    purged = development.loc[~keep].copy()
    retained = development.loc[keep].reset_index(drop=True)
    block_summaries = [
        _block_summary(development, retained, block_id)
        for block_id in range(n_folds + 1)
    ]
    if not all(item["both_classes_after_purge"] for item in block_summaries):
        invalid = [
            item["development_block"]
            for item in block_summaries
            if not item["both_classes_after_purge"]
        ]
        raise ValueError(f"Blocos sem ambas as classes após purga: {invalid}")

    folds: list[dict[str, pd.DataFrame]] = []
    for fold_number in range(1, n_folds + 1):
        fold_train = retained.loc[
            retained["development_block"].lt(fold_number)
        ].copy()
        fold_validation = retained.loc[
            retained["development_block"].eq(fold_number)
        ].copy()
        fold_train["split"] = "train"
        fold_validation["split"] = "validation"
        fold_train = fold_train.reset_index(drop=True)
        fold_validation = fold_validation.reset_index(drop=True)
        _validate_fold(fold_train, fold_validation, fold_number=fold_number)
        folds.append({"train": fold_train, "validation": fold_validation})

    _validate_expanding_nesting(folds)
    audit = {
        "strategy": "attack_active_prefix_boundaries_then_all_future",
        "n_folds": int(n_folds),
        "n_blocks": int(n_folds + 1),
        "active_attack_stop_train_position_exclusive": active_attack_stop,
        "last_attack_stime_in_original_train": int(
            train.iloc[attack_positions[-1]]["Stime"]
        ),
        "boundary_positions_in_development_before_purge": boundary_positions,
        "boundary_stimes": [
            int(development.iloc[position]["Stime"])
            for position in boundary_positions
        ],
        "purge_per_boundary_side_rows": int(purge_per_side),
        "purged_rows_total": int(len(purged)),
        "purged_record_ids_sha256": _record_ids_sha256(
            np.sort(purged["record_id"].to_numpy(dtype=np.int64))
        ),
        "purge_events": purge_events,
        "blocks": block_summaries,
    }
    return folds, audit


def materialize_expanding_temporal_folds(
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    *,
    n_folds: int = DEFAULT_N_FOLDS,
    window_size: int = DEFAULT_WINDOW_SIZE,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Materializa índices de linhas e janelas dos folds de desenvolvimento."""
    source_dir = Path(input_dir)
    destination_dir = Path(output_dir)
    report = Path(report_path)
    inputs = {
        "train": source_dir / "train.parquet",
        "validation": source_dir / "validation.parquet",
    }
    missing = [str(path) for path in inputs.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Partições não encontradas: " + ", ".join(missing))
    output_paths = {
        fold_number: {
            f"{role}_{kind}": destination_dir
            / f"fold_{fold_number}"
            / f"{role}_{kind}.parquet"
            for role in ("train", "validation")
            for kind in ("rows", "window_index")
        }
        for fold_number in range(1, n_folds + 1)
    }
    targets = [
        path for fold_paths in output_paths.values() for path in fold_paths.values()
    ] + [report]
    existing = [str(path) for path in targets if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Saídas já existem; a geração não sobrescreve por padrão: "
            + ", ".join(existing)
        )

    hashes_before = {role: _file_sha256(path) for role, path in inputs.items()}
    metadata_columns = sorted(REQUIRED_COLUMNS)
    train = pd.read_parquet(inputs["train"], columns=metadata_columns)
    validation = pd.read_parquet(inputs["validation"], columns=metadata_columns)
    folds, fold_definition_audit = create_expanding_fold_assignments(
        train,
        validation,
        n_folds=n_folds,
        window_size=window_size,
    )
    del train, validation

    fold_audits: list[dict[str, Any]] = []
    for fold_number, fold in enumerate(folds, start=1):
        paths = output_paths[fold_number]
        role_audits: dict[str, Any] = {}
        for role in ("train", "validation"):
            rows = fold[role]
            row_path = paths[f"{role}_rows"]
            window_path = paths[f"{role}_window_index"]
            manifest, window_blocks = create_partition_window_manifest(
                rows,
                window_size=window_size,
                expected_split=role,
                boundary_columns=["development_block"],
            )
            _atomic_write_parquet(rows, row_path)
            _atomic_write_parquet(manifest, window_path)
            role_audits[role] = {
                "rows_path": str(row_path),
                "rows_sha256": _file_sha256(row_path),
                "rows": int(len(rows)),
                "benign": int(rows["Binary_Label"].eq(0).sum()),
                "attacks": int(rows["Binary_Label"].eq(1).sum()),
                "attack_types": sorted(
                    rows.loc[rows["Binary_Label"].eq(1), "attack_cat"]
                    .astype(str)
                    .unique()
                    .tolist()
                ),
                "development_blocks": sorted(
                    rows["development_block"].astype(int).unique().tolist()
                ),
                "record_ids_sha256": _record_ids_sha256(
                    np.sort(rows["record_id"].to_numpy(dtype=np.int64))
                ),
                "window_index_path": str(window_path),
                "window_index_sha256": _file_sha256(window_path),
                "windows": int(len(manifest)),
                "window_blocks": window_blocks,
            }
        shared = np.intersect1d(
            fold["train"]["record_id"], fold["validation"]["record_id"]
        )
        fold_audits.append(
            {
                "fold": fold_number,
                "train_blocks": list(range(fold_number)),
                "validation_block": fold_number,
                "train_validation_shared_record_ids": int(shared.size),
                "roles": role_audits,
            }
        )

    hashes_after = {role: _file_sha256(path) for role, path in inputs.items()}
    if hashes_before != hashes_after:
        raise RuntimeError("Uma entrada mudou durante a materialização dos folds.")
    test_output = destination_dir / "test.parquet"
    payload = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "expanding_temporal_folds_with_record_purge",
        "shuffle": False,
        "window_size": int(window_size),
        "inputs": {
            role: {
                "path": str(path),
                "sha256_before": hashes_before[role],
                "sha256_after": hashes_after[role],
            }
            for role, path in inputs.items()
        },
        "definition": fold_definition_audit,
        "folds": fold_audits,
        "test_policy": {
            "status": "closed",
            "test_input_was_not_loaded": True,
            "test_output": str(test_output),
            "test_output_exists": test_output.exists(),
        },
        "acceptance": {
            "three_or_more_folds": n_folds >= 3,
            "shuffle_disabled": True,
            "train_grows_monotonically": all(
                len(folds[index]["train"]) < len(folds[index + 1]["train"])
                for index in range(len(folds) - 1)
            ),
            "both_classes_in_every_train_and_validation": all(
                fold[role]["Binary_Label"].nunique() == 2
                for fold in folds
                for role in ("train", "validation")
            ),
            "no_train_validation_record_overlap": all(
                item["train_validation_shared_record_ids"] == 0
                for item in fold_audits
            ),
            "minimum_purge_is_window_size_minus_one": (
                fold_definition_audit["purge_per_boundary_side_rows"]
                == window_size - 1
            ),
            "windows_respect_development_blocks": True,
            "inputs_unchanged": hashes_before == hashes_after,
            "test_remained_closed": not test_output.exists(),
        },
    }
    _atomic_write_json(payload, report)
    return payload


def _attack_active_boundaries(
    train: pd.DataFrame,
    *,
    active_attack_stop: int,
    n_folds: int,
) -> list[int]:
    boundaries: list[int] = []
    for boundary_number in range(1, n_folds + 1):
        position = int(active_attack_stop * boundary_number / (n_folds + 1))
        position = max(1, min(position, active_attack_stop - 1))
        timestamp = int(train.iloc[position]["Stime"])
        while position < active_attack_stop and int(train.iloc[position]["Stime"]) == timestamp:
            position += 1
        if position >= active_attack_stop:
            raise ValueError("Não foi possível separar timestamps na região de ataques.")
        boundaries.append(position)
    if boundaries != sorted(set(boundaries)):
        raise ValueError("As fronteiras temporais calculadas não são únicas.")
    return boundaries


def _validate_input_partition(frame: pd.DataFrame, *, expected_split: str) -> None:
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Metadados temporais ausentes: {missing}")
    if frame.empty:
        raise ValueError(f"Partição vazia: {expected_split}.")
    values = sorted(frame["split"].astype(str).unique().tolist())
    if values != [expected_split]:
        raise ValueError(f"Esperado split={expected_split}; recebido {values}.")
    if not frame["record_id"].is_unique:
        raise ValueError(f"record_id duplicado em {expected_split}.")
    if not frame["Stime"].is_monotonic_increasing:
        raise ValueError(f"Stime não está ordenado em {expected_split}.")
    if frame["Binary_Label"].nunique() != 2:
        raise ValueError(f"{expected_split} deve conter ambas as classes.")


def _validate_fold(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    *,
    fold_number: int,
) -> None:
    if train.empty or validation.empty:
        raise ValueError(f"Fold {fold_number} possui papel vazio.")
    if train["Binary_Label"].nunique() != 2 or validation["Binary_Label"].nunique() != 2:
        raise ValueError(f"Fold {fold_number} não contém ambas as classes.")
    if int(train["Ltime"].max()) >= int(validation["Stime"].min()):
        raise ValueError(f"Fold {fold_number} não preserva ordem cronológica.")
    if np.intersect1d(train["record_id"], validation["record_id"]).size:
        raise ValueError(f"Fold {fold_number} compartilha record_id.")


def _validate_expanding_nesting(folds: list[dict[str, pd.DataFrame]]) -> None:
    for previous, current in zip(folds[:-1], folds[1:]):
        previous_ids = set(previous["train"]["record_id"].astype(int).tolist())
        current_ids = set(current["train"]["record_id"].astype(int).tolist())
        if not previous_ids < current_ids:
            raise ValueError("Os conjuntos de treino não são estritamente expansivos.")


def _block_summary(
    before_purge: pd.DataFrame,
    after_purge: pd.DataFrame,
    block_id: int,
) -> dict[str, Any]:
    before = before_purge.loc[before_purge["development_block"].eq(block_id)]
    after = after_purge.loc[after_purge["development_block"].eq(block_id)]
    return {
        "development_block": int(block_id),
        "rows_before_purge": int(len(before)),
        "rows_after_purge": int(len(after)),
        "start_stime_after_purge": int(after["Stime"].min()),
        "end_ltime_after_purge": int(after["Ltime"].max()),
        "benign_after_purge": int(after["Binary_Label"].eq(0).sum()),
        "attacks_after_purge": int(after["Binary_Label"].eq(1).sum()),
        "both_classes_after_purge": after["Binary_Label"].nunique() == 2,
        "attack_types_after_purge": sorted(
            after.loc[after["Binary_Label"].eq(1), "attack_cat"]
            .astype(str)
            .unique()
            .tolist()
        ),
        "origin_splits": sorted(after["development_origin_split"].unique().tolist()),
        "temporal_sessions": sorted(
            after["temporal_session"].astype(int).unique().tolist()
        ),
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
            raise RuntimeError(f"Contagem divergente no Parquet: {destination}")
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
    parser.add_argument("--n-folds", type=int, default=DEFAULT_N_FOLDS)
    parser.add_argument("--window-size", type=int, default=DEFAULT_WINDOW_SIZE)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    payload = materialize_expanding_temporal_folds(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        report_path=args.report_path,
        n_folds=args.n_folds,
        window_size=args.window_size,
        overwrite=args.overwrite,
    )
    print(json.dumps(payload["acceptance"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
