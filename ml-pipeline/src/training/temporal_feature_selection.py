"""Integração train-only da seleção de atributos ao pipeline temporal.

O seletor é ajustado nas linhas pré-processadas de treino, serializado e só
então aplicado à validação. As saídas preservam os metadados necessários para
que ``partition_window_builder`` realize janelas apenas com as features
selecionadas.

Uso::

    python -m src.training.temporal_feature_selection --top-n 20
"""

from __future__ import annotations

import argparse
import gc
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import config
from src.features.feature_selector import RandomForestFeatureSelector
from src.features.partition_window_builder import iter_partition_window_batches


DEFAULT_INPUT_DIR = Path("data/processed/unsw_nb15_temporal_preprocessed")
DEFAULT_WINDOW_MANIFEST_DIR = Path("data/processed/unsw_nb15_temporal_windows")
DEFAULT_OUTPUT_ROOT = Path("data/processed/unsw_nb15_temporal_selected")
DEFAULT_REPORT_ROOT = Path("reports_temporal/unsw/feature_selection")
SPLITS = ("train", "validation")
METADATA_COLUMNS = (
    "record_id",
    "temporal_session",
    "split",
    "Binary_Label",
    "attack_cat",
    "source_file",
    "Stime",
    "Ltime",
)


def materialize_temporal_feature_selection(
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    window_manifest_dir: str | Path = DEFAULT_WINDOW_MANIFEST_DIR,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    report_root: str | Path = DEFAULT_REPORT_ROOT,
    *,
    top_n: int = 20,
    n_estimators: int = 100,
    n_jobs: int = 1,
    random_state: int = config.RANDOM_SEED,
    window_size: int = config.WINDOW_SIZE,
    window_batch_size: int = 25_000,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Ajusta a seleção no treino e produz partições selecionadas."""
    if top_n < 1:
        raise ValueError("top_n deve ser positivo.")
    input_root = Path(input_dir)
    manifest_root = Path(window_manifest_dir)
    variant = f"top_{top_n}"
    output_dir = Path(output_root) / variant
    report_dir = Path(report_root) / variant
    artifact = report_dir / "feature_selection.json"
    report = report_dir / "selection_audit.json"
    inputs = {split: input_root / f"{split}.parquet" for split in SPLITS}
    manifests = {
        split: manifest_root / f"{split}_window_index.parquet" for split in SPLITS
    }
    outputs = {split: output_dir / f"{split}.parquet" for split in SPLITS}
    required_paths = [*inputs.values(), *manifests.values()]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Entradas não encontradas: " + ", ".join(missing))
    targets = [*outputs.values(), artifact, report]
    existing = [str(path) for path in targets if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Saídas já existem; a geração não sobrescreve por padrão: "
            + ", ".join(existing)
        )

    input_hashes_before = {
        split: _file_sha256(path) for split, path in inputs.items()
    }
    manifest_hashes_before = {
        split: _file_sha256(path) for split, path in manifests.items()
    }

    train = pd.read_parquet(inputs["train"])
    feature_names = _validate_and_get_feature_names(train, expected_split="train")
    X_train = train[feature_names].to_numpy(dtype=np.float32)
    y_train = train["Binary_Label"].to_numpy(dtype=np.int8)
    train_record_ids = train["record_id"].to_numpy(dtype=np.int64)
    selector = RandomForestFeatureSelector(
        feature_names=feature_names,
        top_n=top_n,
        threshold=0.0,
        artifact_path=artifact,
        random_state=random_state,
        n_estimators=n_estimators,
        n_jobs=n_jobs,
    )
    selector.fit(
        X_train,
        y_train,
        partition="train",
        record_ids=train_record_ids,
    )
    selector.save()
    selector_state_before_validation = _selector_state_sha256(selector)

    selected_train = _selected_partition(train, X_train, selector)
    _atomic_write_parquet(selected_train, outputs["train"])
    train_window_audit = _window_realization_audit(
        selected_train,
        selector.selected_feature_names_,
        manifests["train"],
        expected_split="train",
        window_size=window_size,
        batch_size=window_batch_size,
    )
    del train, X_train, y_train, train_record_ids, selected_train
    gc.collect()

    validation = pd.read_parquet(inputs["validation"])
    validation_feature_names = _validate_and_get_feature_names(
        validation, expected_split="validation"
    )
    if validation_feature_names != feature_names:
        raise ValueError("Treino e validação não possuem o mesmo schema de features.")
    X_validation = validation[feature_names].to_numpy(dtype=np.float32)
    selected_validation = _selected_partition(validation, X_validation, selector)
    selector_state_after_validation = _selector_state_sha256(selector)
    if selector_state_before_validation != selector_state_after_validation:
        raise RuntimeError("O estado do seletor mudou ao transformar a validação.")
    _atomic_write_parquet(selected_validation, outputs["validation"])
    validation_window_audit = _window_realization_audit(
        selected_validation,
        selector.selected_feature_names_,
        manifests["validation"],
        expected_split="validation",
        window_size=window_size,
        batch_size=window_batch_size,
    )
    del validation, X_validation, selected_validation
    gc.collect()

    input_hashes_after = {
        split: _file_sha256(path) for split, path in inputs.items()
    }
    manifest_hashes_after = {
        split: _file_sha256(path) for split, path in manifests.items()
    }
    if input_hashes_before != input_hashes_after:
        raise RuntimeError("Uma partição pré-processada mudou durante a seleção.")
    if manifest_hashes_before != manifest_hashes_after:
        raise RuntimeError("Um manifesto de janelas mudou durante a seleção.")

    output_audits = {
        "train": _selected_output_audit(outputs["train"], train_window_audit),
        "validation": _selected_output_audit(
            outputs["validation"], validation_window_audit
        ),
    }
    test_output = output_dir / "test.parquet"
    payload = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "fit_selector_on_train_transform_validation",
        "configuration": {
            "top_n": int(top_n),
            "n_estimators": int(n_estimators),
            "n_jobs": int(n_jobs),
            "random_state": int(random_state),
            "window_size": int(window_size),
        },
        "inputs": {
            split: {
                "path": str(inputs[split]),
                "sha256_before": input_hashes_before[split],
                "sha256_after": input_hashes_after[split],
                "window_manifest": str(manifests[split]),
                "window_manifest_sha256_before": manifest_hashes_before[split],
                "window_manifest_sha256_after": manifest_hashes_after[split],
            }
            for split in SPLITS
        },
        "selection": {
            "fit_partition": selector.fit_partition_,
            "fit_rows": selector.n_training_samples_,
            "fit_record_ids_sha256": selector.fit_record_ids_sha256_,
            "input_feature_count": selector.n_input_features_,
            "selected_feature_count": len(selector.selected_feature_names_),
            "selected_feature_names": selector.selected_feature_names_,
            "selected_feature_names_sha256": _names_sha256(
                selector.selected_feature_names_
            ),
            "selector_state_sha256_before_validation": selector_state_before_validation,
            "selector_state_sha256_after_validation": selector_state_after_validation,
        },
        "artifact": {
            "path": str(artifact),
            "sha256": _file_sha256(artifact),
            "size_bytes": artifact.stat().st_size,
            "serialized_before_validation_was_loaded": True,
        },
        "outputs": output_audits,
        "test_policy": {
            "status": "closed",
            "test_input_was_not_loaded_or_transformed": True,
            "test_output": str(test_output),
            "test_output_exists": test_output.exists(),
        },
        "acceptance": {
            "selector_fit_only_train": selector.fit_partition_ == "train",
            "validation_did_not_change_selector": (
                selector_state_before_validation == selector_state_after_validation
            ),
            "selected_schema_equal_between_train_validation": (
                output_audits["train"]["column_names_sha256"]
                == output_audits["validation"]["column_names_sha256"]
            ),
            "selected_windows_match_step_6_manifests": all(
                audit["window_realization"]["matches_manifest"]
                for audit in output_audits.values()
            ),
            "inputs_and_manifests_unchanged": (
                input_hashes_before == input_hashes_after
                and manifest_hashes_before == manifest_hashes_after
            ),
            "test_remained_closed": not test_output.exists(),
        },
    }
    _atomic_write_json(payload, report)
    return payload


def _validate_and_get_feature_names(
    frame: pd.DataFrame, *, expected_split: str
) -> list[str]:
    missing = sorted(set(METADATA_COLUMNS).difference(frame.columns))
    if missing:
        raise ValueError(f"Metadados obrigatórios ausentes: {missing}")
    split_values = sorted(frame["split"].astype(str).unique().tolist())
    if split_values != [expected_split]:
        raise ValueError(
            f"Esperado split={expected_split}; valores recebidos: {split_values}."
        )
    if not frame["record_id"].is_unique:
        raise ValueError("record_id deve ser único na partição.")
    names = [column for column in frame.columns if column not in METADATA_COLUMNS]
    if not names:
        raise ValueError("Nenhuma feature disponível para seleção.")
    values = frame[names].to_numpy(dtype=np.float32)
    if not np.isfinite(values).all():
        raise ValueError("As features devem ser numéricas e finitas.")
    return names


def _selected_partition(
    raw: pd.DataFrame,
    X: np.ndarray,
    selector: RandomForestFeatureSelector,
) -> pd.DataFrame:
    selected = selector.transform(X).astype(np.float32, copy=False)
    return pd.concat(
        [
            raw[list(METADATA_COLUMNS)].reset_index(drop=True),
            pd.DataFrame(selected, columns=selector.selected_feature_names_),
        ],
        axis=1,
    )


def _window_realization_audit(
    selected: pd.DataFrame,
    feature_names: list[str],
    manifest_path: Path,
    *,
    expected_split: str,
    window_size: int,
    batch_size: int,
) -> dict[str, Any]:
    realized_ids = sha256()
    realized_targets = sha256()
    realized_labels = sha256()
    windows = 0
    for batch in iter_partition_window_batches(
        selected,
        feature_names,
        window_size=window_size,
        batch_size=batch_size,
        expected_split=expected_split,
    ):
        if batch.X.shape[1:] != (window_size, len(feature_names)):
            raise RuntimeError("Dimensão inesperada nas janelas selecionadas.")
        realized_ids.update(
            np.asarray(batch.window_record_ids, dtype="<i8").tobytes()
        )
        realized_targets.update(
            np.asarray(batch.target_record_ids, dtype="<i8").tobytes()
        )
        realized_labels.update(np.asarray(batch.y, dtype=np.int8).tobytes())
        windows += len(batch.y)

    record_columns = [f"record_id_t{offset:02d}" for offset in range(window_size)]
    manifest_ids = sha256()
    manifest_targets = sha256()
    manifest_labels = sha256()
    manifest_windows = 0
    parquet = pq.ParquetFile(manifest_path)
    for arrow_batch in parquet.iter_batches(
        batch_size=batch_size,
        columns=[*record_columns, "target_record_id", "Binary_Label"],
    ):
        frame = arrow_batch.to_pandas()
        manifest_ids.update(
            np.asarray(frame[record_columns], dtype="<i8").tobytes()
        )
        manifest_targets.update(
            np.asarray(frame["target_record_id"], dtype="<i8").tobytes()
        )
        manifest_labels.update(
            np.asarray(frame["Binary_Label"], dtype=np.int8).tobytes()
        )
        manifest_windows += len(frame)

    realized = {
        "windows": windows,
        "window_record_ids_sha256": realized_ids.hexdigest(),
        "target_record_ids_sha256": realized_targets.hexdigest(),
        "labels_sha256": realized_labels.hexdigest(),
    }
    expected = {
        "windows": manifest_windows,
        "window_record_ids_sha256": manifest_ids.hexdigest(),
        "target_record_ids_sha256": manifest_targets.hexdigest(),
        "labels_sha256": manifest_labels.hexdigest(),
    }
    return {
        "selected_feature_shape_per_window": [window_size, len(feature_names)],
        "tabular_feature_count_per_window": window_size * len(feature_names),
        "realized": realized,
        "manifest": expected,
        "matches_manifest": realized == expected,
    }


def _selected_output_audit(
    path: Path, window_realization: dict[str, Any]
) -> dict[str, Any]:
    parquet = pq.ParquetFile(path)
    names = parquet.schema_arrow.names
    return {
        "path": str(path),
        "sha256": _file_sha256(path),
        "size_bytes": path.stat().st_size,
        "rows": int(parquet.metadata.num_rows),
        "columns": int(parquet.metadata.num_columns),
        "column_names_sha256": _names_sha256(names),
        "window_realization": window_realization,
    }


def _selector_state_sha256(selector: RandomForestFeatureSelector) -> str:
    payload = json.dumps(selector.to_dict(), sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _names_sha256(names: list[str]) -> str:
    return sha256("\n".join(names).encode("utf-8")).hexdigest()


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
    parser.add_argument("--window-manifest-dir", default=str(DEFAULT_WINDOW_MANIFEST_DIR))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--report-root", default=str(DEFAULT_REPORT_ROOT))
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--window-size", type=int, default=config.WINDOW_SIZE)
    parser.add_argument("--window-batch-size", type=int, default=25_000)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    payload = materialize_temporal_feature_selection(
        input_dir=args.input_dir,
        window_manifest_dir=args.window_manifest_dir,
        output_root=args.output_root,
        report_root=args.report_root,
        top_n=args.top_n,
        n_estimators=args.n_estimators,
        n_jobs=args.n_jobs,
        window_size=args.window_size,
        window_batch_size=args.window_batch_size,
        overwrite=args.overwrite,
    )
    print(json.dumps(payload["acceptance"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
