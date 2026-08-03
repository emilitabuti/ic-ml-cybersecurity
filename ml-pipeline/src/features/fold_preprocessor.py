"""Pré-processamento ajustado exclusivamente na partição de treino.

O componente mantém metadados temporais fora das features, normaliza campos
numéricos representados como texto, aprende ``log1p``, ``RobustScaler`` e as
categorias do ``OneHotEncoder`` somente no treino e reutiliza esse estado sem
refit nas demais partições.

Uso para materializar o conjunto de desenvolvimento do UNSW-NB15::

    python -m src.features.fold_preprocessor

O comando lê e escreve apenas treino e validação. O teste temporal permanece
fechado até o protocolo e os hiperparâmetros serem congelados.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.preprocessing import OneHotEncoder, RobustScaler


DEFAULT_INPUT_DIR = Path("data/processed/unsw_nb15_temporal")
DEFAULT_OUTPUT_DIR = Path("data/processed/unsw_nb15_temporal_preprocessed")
DEFAULT_ARTIFACT_PATH = Path(
    "reports_temporal/unsw/preprocessing/train_only_preprocessor.joblib"
)
DEFAULT_REPORT_PATH = Path(
    "reports_temporal/unsw/preprocessing/preprocessing_audit.json"
)
LOG1P_MAX_THRESHOLD = 1_000_000.0
CATEGORICAL_CANDIDATES = ("proto", "state", "service")
NON_FEATURE_COLUMNS = {
    "Binary_Label",
    "Attack_Type",
    "Attack_Type_ID",
    "Label",
    "attack_cat",
    "label",
    "source_file",
    "srcip",
    "dstip",
    "record_id",
    "temporal_session",
    "split",
    "Stime",
    "Ltime",
}
PASSTHROUGH_METADATA_COLUMNS = (
    "record_id",
    "temporal_session",
    "split",
    "Binary_Label",
    "attack_cat",
    "source_file",
    "Stime",
    "Ltime",
)


class FoldPreprocessor:
    """Transformador com estado explícito e ajuste restrito ao treino."""

    def __init__(self, *, log1p_max_threshold: float = LOG1P_MAX_THRESHOLD) -> None:
        self.log1p_max_threshold = float(log1p_max_threshold)
        self.numeric_columns_: list[str] = []
        self.categorical_columns_: list[str] = []
        self.log1p_columns_: list[str] = []
        self.feature_names_out_: list[str] = []
        self.scaler_: RobustScaler | None = None
        self.encoder_: OneHotEncoder | None = None
        self.fit_record_ids_sha256_: str | None = None
        self.fit_rows_: int | None = None
        self.fit_split_values_: list[str] = []
        self.is_fitted_ = False

    def fit(self, frame: pd.DataFrame) -> "FoldPreprocessor":
        """Aprende transformações; aceita somente linhas marcadas como treino."""
        if self.is_fitted_:
            raise RuntimeError("O pré-processador já foi ajustado; refit é proibido.")
        if frame.empty:
            raise ValueError("A partição de treino não pode estar vazia.")
        if "split" not in frame.columns:
            raise ValueError("A coluna split é obrigatória para provar o ajuste no treino.")
        split_values = sorted(frame["split"].dropna().astype(str).unique().tolist())
        if split_values != ["train"]:
            raise ValueError(
                "fit() aceita exclusivamente a partição train; "
                f"valores recebidos: {split_values}."
            )
        if "record_id" not in frame.columns:
            raise ValueError("record_id é obrigatório para auditar as linhas de ajuste.")
        if not frame["record_id"].is_unique:
            raise ValueError("record_id deve ser único dentro da partição de treino.")

        self.categorical_columns_ = [
            column for column in CATEGORICAL_CANDIDATES if column in frame.columns
        ]
        self.numeric_columns_ = [
            column
            for column in frame.columns
            if column not in NON_FEATURE_COLUMNS
            and column not in self.categorical_columns_
        ]
        if not self.numeric_columns_ and not self.categorical_columns_:
            raise ValueError("Nenhuma feature foi encontrada na partição de treino.")

        numeric = self._numeric_matrix(frame)
        self.log1p_columns_ = [
            column
            for index, column in enumerate(self.numeric_columns_)
            if float(np.min(numeric[:, index])) >= 0.0
            and float(np.max(numeric[:, index])) > self.log1p_max_threshold
        ]
        numeric = self._apply_log1p(numeric)
        self.scaler_ = RobustScaler()
        self.scaler_.fit(numeric)

        self.encoder_ = OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=False,
            dtype=np.float32,
        )
        if self.categorical_columns_:
            self.encoder_.fit(self._categorical_frame(frame))
            encoded_names = self.encoder_.get_feature_names_out(
                self.categorical_columns_
            ).tolist()
        else:
            encoded_names = []

        self.feature_names_out_ = [*self.numeric_columns_, *encoded_names]
        self.fit_record_ids_sha256_ = _record_ids_sha256(
            frame["record_id"].to_numpy(dtype=np.int64)
        )
        self.fit_rows_ = int(len(frame))
        self.fit_split_values_ = split_values
        self.is_fitted_ = True
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Aplica o estado aprendido sem alterar qualquer parâmetro."""
        self._require_fitted()
        required = set(self.numeric_columns_) | set(self.categorical_columns_)
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"Features obrigatórias ausentes: {missing}")

        assert self.scaler_ is not None
        numeric = self._apply_log1p(self._numeric_matrix(frame))
        scaled = self.scaler_.transform(numeric).astype(np.float32, copy=False)

        if self.categorical_columns_:
            assert self.encoder_ is not None
            encoded = self.encoder_.transform(
                self._categorical_frame(frame)
            ).astype(np.float32, copy=False)
            values = np.concatenate((scaled, encoded), axis=1)
        else:
            values = scaled
        return pd.DataFrame(values, columns=self.feature_names_out_)

    def get_feature_names_out(self) -> list[str]:
        """Retorna uma cópia da ordem estável das features transformadas."""
        self._require_fitted()
        return list(self.feature_names_out_)

    def audit_metadata(self) -> dict[str, Any]:
        """Expõe a evidência serializável de como o estado foi aprendido."""
        self._require_fitted()
        assert self.scaler_ is not None
        assert self.encoder_ is not None
        categories = (
            {
                column: values.astype(str).tolist()
                for column, values in zip(
                    self.categorical_columns_, self.encoder_.categories_, strict=True
                )
            }
            if self.categorical_columns_
            else {}
        )
        return {
            "fit_partition": "train",
            "fit_split_values": list(self.fit_split_values_),
            "fit_rows": self.fit_rows_,
            "fit_record_ids_sha256": self.fit_record_ids_sha256_,
            "numeric_columns": list(self.numeric_columns_),
            "categorical_columns": list(self.categorical_columns_),
            "log1p_columns": list(self.log1p_columns_),
            "log1p_max_threshold": self.log1p_max_threshold,
            "one_hot_handle_unknown": "ignore",
            "categories_learned_from_train": categories,
            "output_feature_names": list(self.feature_names_out_),
            "output_feature_count": len(self.feature_names_out_),
            "scaler_center": self.scaler_.center_.astype(float).tolist(),
            "scaler_scale": self.scaler_.scale_.astype(float).tolist(),
            "excluded_from_features": sorted(NON_FEATURE_COLUMNS),
        }

    def save(self, destination: str | Path) -> None:
        """Serializa atomicamente o estado já ajustado."""
        self._require_fitted()
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        try:
            payload = {
                "artifact_type": "FoldPreprocessor",
                "artifact_version": "1.0",
                "state": self.__dict__,
            }
            joblib.dump(payload, temporary)
            restored = joblib.load(temporary)
            if (
                not isinstance(restored, dict)
                or restored.get("artifact_type") != "FoldPreprocessor"
            ):
                raise RuntimeError("O artefato temporário não pôde ser validado.")
            temporary.replace(path)
        finally:
            if temporary.exists():
                temporary.unlink()

    @classmethod
    def load(cls, source: str | Path) -> "FoldPreprocessor":
        """Carrega um artefato e valida seu tipo e estado."""
        payload = joblib.load(Path(source))
        if (
            not isinstance(payload, dict)
            or payload.get("artifact_type") != "FoldPreprocessor"
            or not isinstance(payload.get("state"), dict)
        ):
            raise ValueError("O arquivo não contém um FoldPreprocessor ajustado.")
        restored = cls()
        restored.__dict__.update(payload["state"])
        if not restored.is_fitted_:
            raise ValueError("O arquivo não contém um FoldPreprocessor ajustado.")
        return restored

    def _numeric_matrix(self, frame: pd.DataFrame) -> np.ndarray:
        columns = [_coerce_numeric(frame[column]) for column in self.numeric_columns_]
        if not columns:
            return np.empty((len(frame), 0), dtype=np.float64)
        return np.column_stack(columns)

    def _categorical_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            {
                column: frame[column].astype("string").fillna("__MISSING__")
                for column in self.categorical_columns_
            }
        )

    def _apply_log1p(self, numeric: np.ndarray) -> np.ndarray:
        if not self.log1p_columns_:
            return numeric
        result = numeric.copy()
        positions = [self.numeric_columns_.index(column) for column in self.log1p_columns_]
        result[:, positions] = np.log1p(np.clip(result[:, positions], 0.0, None))
        return result

    def _require_fitted(self) -> None:
        if not self.is_fitted_:
            raise RuntimeError("Execute fit() na partição de treino antes de transformar.")


def materialize_train_validation_preprocessing(
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    artifact_path: str | Path = DEFAULT_ARTIFACT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    *,
    batch_size: int = 100_000,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Ajusta no treino e materializa somente treino e validação em lotes."""
    if batch_size < 1:
        raise ValueError("batch_size deve ser positivo.")
    source_dir = Path(input_dir)
    destination_dir = Path(output_dir)
    artifact = Path(artifact_path)
    report = Path(report_path)
    inputs = {
        "train": source_dir / "train.parquet",
        "validation": source_dir / "validation.parquet",
    }
    outputs = {
        "train": destination_dir / "train.parquet",
        "validation": destination_dir / "validation.parquet",
    }
    missing = [str(path) for path in inputs.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Partições não encontradas: " + ", ".join(missing))
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
    train = pd.read_parquet(inputs["train"])
    preprocessor = FoldPreprocessor().fit(train)
    preprocessor_metadata = preprocessor.audit_metadata()
    preprocessor.save(artifact)
    del train

    partition_audits: dict[str, Any] = {}
    for split in ("train", "validation"):
        partition_audits[split] = _materialize_partition_in_batches(
            inputs[split],
            outputs[split],
            preprocessor,
            expected_split=split,
            batch_size=batch_size,
        )

    input_hashes_after = {
        split: _file_sha256(path) for split, path in inputs.items()
    }
    if input_hashes_before != input_hashes_after:
        raise RuntimeError("Uma partição de entrada mudou durante o pré-processamento.")

    payload = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "fit_train_transform_train_validation",
        "inputs": {
            split: {
                "path": str(path),
                "sha256_before": input_hashes_before[split],
                "sha256_after": input_hashes_after[split],
            }
            for split, path in inputs.items()
        },
        "preprocessor": preprocessor_metadata,
        "artifact": {
            "path": str(artifact),
            "sha256": _file_sha256(artifact),
            "size_bytes": artifact.stat().st_size,
            "serialized_before_validation_transform": True,
        },
        "outputs": partition_audits,
        "test_policy": {
            "status": "closed",
            "test_input_was_not_loaded_or_transformed": True,
            "test_output_path": str(destination_dir / "test.parquet"),
            "test_output_exists": (destination_dir / "test.parquet").exists(),
        },
        "acceptance": {
            "fit_used_only_train": preprocessor.fit_split_values_ == ["train"],
            "train_and_validation_inputs_unchanged": (
                input_hashes_before == input_hashes_after
            ),
            "same_feature_schema_in_train_and_validation": (
                partition_audits["train"]["column_names_sha256"]
                == partition_audits["validation"]["column_names_sha256"]
            ),
            "timestamps_excluded_from_features": not {
                "Stime",
                "Ltime",
            }.intersection(preprocessor.feature_names_out_),
            "test_remained_closed": not (destination_dir / "test.parquet").exists(),
        },
    }
    _atomic_write_json(payload, report)
    return payload


def _coerce_numeric(series: pd.Series) -> np.ndarray:
    """Converte decimais e portas hexadecimais; inválidos tornam-se zero."""
    if pd.api.types.is_numeric_dtype(series.dtype):
        numeric = pd.to_numeric(series, errors="coerce")
    else:
        text = series.astype("string").str.strip()
        numeric = pd.to_numeric(text, errors="coerce")
        unresolved = numeric.isna() & text.str.match(r"^[+-]?0[xX][0-9a-fA-F]+$", na=False)
        if unresolved.any():
            numeric.loc[unresolved] = text.loc[unresolved].map(lambda value: int(value, 16))
    values = numeric.to_numpy(dtype=np.float64, na_value=np.nan)
    values[~np.isfinite(values)] = 0.0
    return values


def _materialize_partition_in_batches(
    source: Path,
    destination: Path,
    preprocessor: FoldPreprocessor,
    *,
    expected_split: str,
    batch_size: int,
) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)

    writer: pq.ParquetWriter | None = None
    rows = 0
    record_digest = sha256()
    try:
        parquet = pq.ParquetFile(source)
        for batch in parquet.iter_batches(batch_size=batch_size):
            raw = batch.to_pandas()
            split_values = sorted(raw["split"].astype(str).unique().tolist())
            if split_values != [expected_split]:
                raise ValueError(
                    f"{source} contém splits inesperados: {split_values}."
                )
            transformed = preprocessor.transform(raw)
            metadata_columns = [
                column for column in PASSTHROUGH_METADATA_COLUMNS if column in raw.columns
            ]
            output = pd.concat(
                [
                    raw[metadata_columns].reset_index(drop=True),
                    transformed.reset_index(drop=True),
                ],
                axis=1,
            )
            table = pa.Table.from_pandas(output, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(temporary, table.schema, compression="snappy")
            writer.write_table(table)
            ids = raw["record_id"].to_numpy(dtype="<i8")
            record_digest.update(ids.tobytes())
            rows += len(raw)
        if writer is None:
            raise ValueError(f"Partição vazia: {source}")
        writer.close()
        writer = None
        check = pq.ParquetFile(temporary)
        if check.metadata.num_rows != rows:
            raise RuntimeError(f"Contagem divergente no Parquet temporário: {source}")
        temporary.replace(destination)
    finally:
        if writer is not None:
            writer.close()
        if temporary.exists():
            temporary.unlink()

    parquet = pq.ParquetFile(destination)
    column_names = parquet.schema_arrow.names
    return {
        "path": str(destination),
        "sha256": _file_sha256(destination),
        "size_bytes": destination.stat().st_size,
        "rows": int(parquet.metadata.num_rows),
        "columns": int(parquet.metadata.num_columns),
        "column_names_sha256": sha256(
            "\n".join(column_names).encode("utf-8")
        ).hexdigest(),
        "feature_count": len(preprocessor.feature_names_out_),
        "record_ids_sha256": record_digest.hexdigest(),
        "split": expected_split,
    }


def _record_ids_sha256(record_ids: np.ndarray) -> str:
    return sha256(np.asarray(record_ids, dtype="<i8").tobytes()).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    parser.add_argument("--artifact-path", default=str(DEFAULT_ARTIFACT_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--batch-size", type=int, default=100_000)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    payload = materialize_train_validation_preprocessing(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        artifact_path=args.artifact_path,
        report_path=args.report_path,
        batch_size=args.batch_size,
        overwrite=args.overwrite,
    )
    print(json.dumps(payload["acceptance"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
