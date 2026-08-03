"""Experimentos temporais retomáveis no desenvolvimento do UNSW-NB15.

Cada fold reajusta pré-processador e ranking de atributos apenas em seu treino.
Baseline e ``top_n`` compartilham linhas, janelas, ranking e hiperparâmetros.
Resultados são persistidos por fold imediatamente; o teste fechado não é uma
entrada deste módulo.
"""

from __future__ import annotations

import argparse
import gc
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from time import perf_counter
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

import config
from src.features.feature_selector import RandomForestFeatureSelector
from src.features.fold_preprocessor import FoldPreprocessor
from src.features.partition_window_builder import iter_partition_window_batches
from src.training.metrics import METRIC_NAMES, calculate_binary_metrics


DEFAULT_RAW_DIR = Path("data/processed/unsw_nb15_temporal")
DEFAULT_FOLD_DIR = Path("data/processed/unsw_nb15_temporal_folds")
DEFAULT_CACHE_DIR = Path("data/processed/unsw_nb15_temporal_experiment_folds")
DEFAULT_REPORT_DIR = Path("reports_temporal/unsw/development_experiments")
DEFAULT_VARIANTS = ("all", "top_10", "top_20", "top_30")
DEFAULT_ALGORITHMS = ("decision_tree", "random_forest", "lstm")
WINDOW_METADATA = (
    "record_id",
    "temporal_session",
    "split",
    "Binary_Label",
    "attack_cat",
    "source_file",
    "Stime",
    "Ltime",
    "development_block",
    "development_origin_split",
)


def prepare_experiment_fold_caches(
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    fold_dir: str | Path = DEFAULT_FOLD_DIR,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    *,
    folds: Iterable[int] = (1, 2, 3),
    selector_n_estimators: int = 100,
    selector_n_jobs: int = 2,
    overwrite: bool = False,
) -> list[dict[str, Any]]:
    """Materializa transformações e ranking train-only específicos de cada fold."""
    fold_numbers = tuple(int(value) for value in folds)
    raw_root = Path(raw_dir)
    fold_root = Path(fold_dir)
    cache_root = Path(cache_dir)
    report_root = Path(report_dir)
    raw_paths = [raw_root / "train.parquet", raw_root / "validation.parquet"]
    missing = [str(path) for path in raw_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Dados brutos de desenvolvimento ausentes: " + ", ".join(missing))

    targets: list[Path] = []
    for fold in fold_numbers:
        targets.extend(
            [
                cache_root / f"fold_{fold}" / "train.parquet",
                cache_root / f"fold_{fold}" / "validation.parquet",
                report_root / f"fold_{fold}" / "preprocessor.joblib",
                report_root / f"fold_{fold}" / "feature_ranking.json",
                report_root / f"fold_{fold}" / "preparation_audit.json",
            ]
        )
    existing = [path for path in targets if path.exists()]
    if existing and not overwrite:
        # Um cache completo é reutilizável; estado parcial exige overwrite explícito.
        if all(path.exists() for path in targets):
            return [
                json.loads(
                    (report_root / f"fold_{fold}" / "preparation_audit.json").read_text(
                        encoding="utf-8"
                    )
                )
                for fold in fold_numbers
            ]
        raise FileExistsError(
            "Cache parcial já existe; use overwrite para reconstruir: "
            + ", ".join(str(path) for path in existing)
        )

    raw_frames = [pd.read_parquet(path) for path in raw_paths]
    raw = pd.concat(raw_frames, ignore_index=True)
    del raw_frames
    if not raw["record_id"].is_unique:
        raise ValueError("record_id não é único no desenvolvimento bruto.")
    raw_indexed = raw.set_index("record_id", drop=False)
    audits: list[dict[str, Any]] = []

    for fold in fold_numbers:
        fold_cache = cache_root / f"fold_{fold}"
        fold_report = report_root / f"fold_{fold}"
        row_paths = {
            role: fold_root / f"fold_{fold}" / f"{role}_rows.parquet"
            for role in ("train", "validation")
        }
        row_indices = {role: pd.read_parquet(path) for role, path in row_paths.items()}
        raw_roles: dict[str, pd.DataFrame] = {}
        for role in ("train", "validation"):
            ids = row_indices[role]["record_id"].to_numpy(dtype=np.int64)
            role_raw = raw_indexed.loc[ids].reset_index(drop=True).copy()
            role_raw["split"] = role
            raw_roles[role] = role_raw

        preprocessor = FoldPreprocessor().fit(raw_roles["train"])
        preprocessor_path = fold_report / "preprocessor.joblib"
        preprocessor.save(preprocessor_path)
        X_train = preprocessor.transform(raw_roles["train"])
        feature_names = X_train.columns.tolist()
        ranking = RandomForestFeatureSelector(
            feature_names=feature_names,
            top_n=min(30, len(feature_names)),
            threshold=0.0,
            artifact_path=fold_report / "feature_ranking.json",
            random_state=config.RANDOM_SEED,
            n_estimators=selector_n_estimators,
            n_jobs=selector_n_jobs,
        ).fit(
            X_train.to_numpy(dtype=np.float32),
            raw_roles["train"]["Binary_Label"].to_numpy(dtype=np.int8),
            partition="train",
            record_ids=raw_roles["train"]["record_id"].to_numpy(dtype=np.int64),
        )
        ranking.save()
        ranking_state = _selector_state_sha256(ranking)

        output_audit: dict[str, Any] = {}
        for role in ("train", "validation"):
            transformed = (
                X_train if role == "train" else preprocessor.transform(raw_roles[role])
            )
            metadata = row_indices[role][list(WINDOW_METADATA)].reset_index(drop=True)
            output = pd.concat([metadata, transformed.reset_index(drop=True)], axis=1)
            destination = fold_cache / f"{role}.parquet"
            _atomic_write_parquet(output, destination)
            output_audit[role] = {
                "path": str(destination),
                "sha256": _file_sha256(destination),
                "rows": int(len(output)),
                "columns": int(len(output.columns)),
                "record_ids_sha256": _record_ids_sha256(
                    output["record_id"].to_numpy(dtype=np.int64)
                ),
            }
            del output, transformed
        if _selector_state_sha256(ranking) != ranking_state:
            raise RuntimeError("A transformação da validação alterou o ranking.")

        audit = {
            "fold": fold,
            "fit_partition": "train",
            "input_feature_count": len(feature_names),
            "ranking_feature_count": len(ranking.selected_feature_names_),
            "ranking_feature_names": ranking.selected_feature_names_,
            "preprocessor_path": str(preprocessor_path),
            "preprocessor_sha256": _file_sha256(preprocessor_path),
            "ranking_path": str(ranking.artifact_path),
            "ranking_sha256": _file_sha256(ranking.artifact_path),
            "selector_state_unchanged_by_validation": True,
            "outputs": output_audit,
            "test_used": False,
        }
        _atomic_write_json(audit, fold_report / "preparation_audit.json")
        audits.append(audit)
        del raw_roles, row_indices, X_train, preprocessor, ranking
        gc.collect()

    del raw, raw_indexed
    gc.collect()
    return audits


def run_development_experiments(
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    *,
    algorithms: Iterable[str] = DEFAULT_ALGORITHMS,
    variants: Iterable[str] = DEFAULT_VARIANTS,
    folds: Iterable[int] = (1, 2, 3),
    window_size: int = config.WINDOW_SIZE,
    batch_size: int = 25_000,
    rf_n_estimators: int = config.RF_N_ESTIMATORS,
    lstm_epochs: int = config.LSTM_EPOCHS,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Executa modelos/variantes, persistindo cada fold para permitir retomada."""
    cache_root = Path(cache_dir)
    report_root = Path(report_dir)
    algorithm_names = tuple(algorithms)
    variant_names = tuple(variants)
    fold_numbers = tuple(int(value) for value in folds)
    invalid_algorithms = sorted(set(algorithm_names).difference(DEFAULT_ALGORITHMS))
    if invalid_algorithms:
        raise ValueError(f"Algoritmos inválidos: {invalid_algorithms}")
    _validate_variants(variant_names)

    for fold in fold_numbers:
        ranking_path = report_root / f"fold_{fold}" / "feature_ranking.json"
        ranking = RandomForestFeatureSelector.load(ranking_path)
        all_features = ranking.feature_names
        for variant in variant_names:
            features = _variant_features(variant, all_features, ranking)
            for algorithm in algorithm_names:
                result_path = (
                    report_root
                    / "results"
                    / algorithm
                    / variant
                    / f"fold_{fold}.json"
                )
                if result_path.exists() and not overwrite:
                    continue
                train = pd.read_parquet(
                    cache_root / f"fold_{fold}" / "train.parquet",
                    columns=[*WINDOW_METADATA, *features],
                )
                validation = pd.read_parquet(
                    cache_root / f"fold_{fold}" / "validation.parquet",
                    columns=[*WINDOW_METADATA, *features],
                )
                result = _run_one(
                    algorithm,
                    variant,
                    fold,
                    train,
                    validation,
                    features,
                    window_size=window_size,
                    batch_size=batch_size,
                    rf_n_estimators=rf_n_estimators,
                    lstm_epochs=lstm_epochs,
                )
                _atomic_write_json(result, result_path)
                del train, validation
                gc.collect()

    return aggregate_development_results(report_root, expected_folds=fold_numbers)


def aggregate_development_results(
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    *,
    expected_folds: Iterable[int] = (1, 2, 3),
) -> dict[str, Any]:
    """Agrega apenas combinações completas, sem consultar o teste."""
    report_root = Path(report_dir)
    expected = set(int(value) for value in expected_folds)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for path in sorted((report_root / "results").glob("*/*/fold_*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        grouped.setdefault((item["algorithm"], item["variant"]), []).append(item)

    rows: list[dict[str, Any]] = []
    for (algorithm, variant), results in sorted(grouped.items()):
        folds_present = {int(item["fold"]) for item in results}
        if folds_present != expected:
            continue
        feature_counts = [int(item["feature_count"]) for item in results]
        row: dict[str, Any] = {
            "algorithm": algorithm,
            "variant": variant,
            "feature_count": (
                feature_counts[0] if len(set(feature_counts)) == 1 else None
            ),
            "feature_count_min": min(feature_counts),
            "feature_count_max": max(feature_counts),
            "feature_count_by_fold": feature_counts,
            "folds": len(results),
            "fit_seconds_mean": float(np.mean([item["fit_seconds"] for item in results])),
            "inference_seconds_mean": float(
                np.mean([item["inference_seconds"] for item in results])
            ),
        }
        for metric in METRIC_NAMES:
            values = np.asarray([item["metrics"][metric] for item in results], dtype=float)
            row[f"{metric}_mean"] = float(np.nanmean(values))
            row[f"{metric}_std"] = float(np.nanstd(values))
        rows.append(row)
    comparison = pd.DataFrame(rows)
    comparison_path = report_root / "comparison_metrics.csv"
    comparison_path.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(comparison_path, index=False)
    payload = {
        "protocol": "temporal_purged_expanding_folds",
        "test_used": False,
        "complete_configurations": len(rows),
        "comparison_csv": str(comparison_path),
        "rows": rows,
    }
    _atomic_write_json(payload, report_root / "development_summary.json")
    return payload


def _run_one(
    algorithm: str,
    variant: str,
    fold: int,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    features: list[str],
    *,
    window_size: int,
    batch_size: int,
    rf_n_estimators: int,
    lstm_epochs: int,
) -> dict[str, Any]:
    print(
        f"[temporal] algoritmo={algorithm} variante={variant} fold={fold} iniciando",
        flush=True,
    )
    started = perf_counter()
    if algorithm == "lstm":
        model, fit_seconds = _fit_lstm(
            train,
            features,
            window_size=window_size,
            batch_size=batch_size,
            epochs=lstm_epochs,
        )
    else:
        X_train, y_train = _collect_train_windows(
            train,
            features,
            flatten=True,
            window_size=window_size,
            batch_size=batch_size,
        )
        if algorithm == "decision_tree":
            model = DecisionTreeClassifier(
                max_depth=int(config.DT_MAX_DEPTH) if config.DT_MAX_DEPTH else None,
                random_state=config.RANDOM_SEED,
            )
        else:
            model = RandomForestClassifier(
                n_estimators=rf_n_estimators,
                max_depth=int(config.RF_MAX_DEPTH) if config.RF_MAX_DEPTH else None,
                random_state=config.RANDOM_SEED,
                n_jobs=config.RF_N_JOBS,
            )
        fit_start = perf_counter()
        model.fit(X_train, y_train)
        fit_seconds = perf_counter() - fit_start
        del X_train, y_train
        gc.collect()

    inference_start = perf_counter()
    y_true, y_pred, y_score = _predict_in_batches(
        model,
        algorithm,
        validation,
        features,
        window_size=window_size,
        batch_size=batch_size,
    )
    inference_seconds = perf_counter() - inference_start
    metrics = calculate_binary_metrics(y_true, y_pred, y_score)
    artifact_size = _serialized_size_bytes(model, algorithm)
    result = {
        "protocol": "temporal_purged_expanding_folds",
        "shuffle": False,
        "test_used": False,
        "algorithm": algorithm,
        "variant": variant,
        "fold": int(fold),
        "feature_count": len(features),
        "feature_names": features,
        "feature_names_sha256": _names_sha256(features),
        "window_size": int(window_size),
        "model_input_shape": (
            [window_size, len(features)]
            if algorithm == "lstm"
            else [window_size * len(features)]
        ),
        "train_windows": int(_window_count(train, window_size)),
        "validation_windows": int(len(y_true)),
        "fit_seconds": float(fit_seconds),
        "inference_seconds": float(inference_seconds),
        "artifact_size_bytes": int(artifact_size),
        "metrics": metrics,
        "total_seconds": float(perf_counter() - started),
    }
    print(
        f"[temporal] algoritmo={algorithm} variante={variant} fold={fold} "
        f"f1={metrics['f1']:.6f} pr_auc={metrics['pr_auc']:.6f} concluído",
        flush=True,
    )
    if algorithm == "lstm":
        import tensorflow as tf

        tf.keras.backend.clear_session()
    del model, y_true, y_pred, y_score
    gc.collect()
    return result


def _collect_train_windows(
    frame: pd.DataFrame,
    features: list[str],
    *,
    flatten: bool,
    window_size: int,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    X_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    for batch in iter_partition_window_batches(
        frame,
        features,
        window_size=window_size,
        batch_size=batch_size,
        expected_split="train",
        boundary_columns=["development_block"],
    ):
        X_parts.append(batch.flatten() if flatten else batch.X)
        y_parts.append(batch.y.astype(np.int8, copy=False))
    return np.concatenate(X_parts), np.concatenate(y_parts)


def _predict_in_batches(
    model: Any,
    algorithm: str,
    frame: pd.DataFrame,
    features: list[str],
    *,
    window_size: int,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    true_parts: list[np.ndarray] = []
    pred_parts: list[np.ndarray] = []
    score_parts: list[np.ndarray] = []
    for batch in iter_partition_window_batches(
        frame,
        features,
        window_size=window_size,
        batch_size=batch_size,
        expected_split="validation",
        boundary_columns=["development_block"],
    ):
        values = batch.X if algorithm == "lstm" else batch.flatten()
        if algorithm == "lstm":
            score = np.asarray(model.predict_on_batch(values)).reshape(-1)
        else:
            score = np.asarray(model.predict_proba(values))[:, 1]
        true_parts.append(batch.y.astype(np.int8, copy=False))
        score_parts.append(score.astype(np.float64, copy=False))
        pred_parts.append((score >= 0.5).astype(np.int8))
    return np.concatenate(true_parts), np.concatenate(pred_parts), np.concatenate(score_parts)


def _fit_lstm(
    train: pd.DataFrame,
    features: list[str],
    *,
    window_size: int,
    batch_size: int,
    epochs: int,
) -> tuple[Any, float]:
    try:
        import tensorflow as tf
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "TensorFlow real é obrigatório; execute com .venv-tf/bin/python."
        ) from exc
    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(config.RANDOM_SEED)
    try:
        tf.config.experimental.enable_op_determinism()
    except (AttributeError, RuntimeError):
        pass

    def generator():
        for batch in iter_partition_window_batches(
            train,
            features,
            window_size=window_size,
            batch_size=batch_size,
            expected_split="train",
            boundary_columns=["development_block"],
        ):
            yield batch.X, batch.y.astype(np.float32)

    dataset = tf.data.Dataset.from_generator(
        generator,
        output_signature=(
            tf.TensorSpec((None, window_size, len(features)), tf.float32),
            tf.TensorSpec((None,), tf.float32),
        ),
    ).repeat().prefetch(1)
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input((window_size, len(features))),
            tf.keras.layers.LSTM(64),
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(optimizer="adam", loss="binary_crossentropy")
    started = perf_counter()
    model.fit(
        dataset,
        epochs=epochs,
        steps_per_epoch=_window_batch_count(train, window_size, batch_size),
        shuffle=False,
        verbose=2,
    )
    return model, perf_counter() - started


def _window_count(frame: pd.DataFrame, window_size: int) -> int:
    change = (
        frame["development_block"].ne(frame["development_block"].shift())
        | frame["temporal_session"].ne(frame["temporal_session"].shift())
        | frame["source_file"].ne(frame["source_file"].shift())
    )
    return int(
        sum(max(0, int(count) - window_size + 1) for count in change.cumsum().value_counts())
    )


def _window_batch_count(
    frame: pd.DataFrame, window_size: int, batch_size: int
) -> int:
    change = (
        frame["development_block"].ne(frame["development_block"].shift())
        | frame["temporal_session"].ne(frame["temporal_session"].shift())
        | frame["source_file"].ne(frame["source_file"].shift())
    )
    windows_per_block = [
        max(0, int(count) - window_size + 1)
        for count in change.cumsum().value_counts(sort=False)
    ]
    return int(sum((windows + batch_size - 1) // batch_size for windows in windows_per_block if windows))


def _variant_features(
    variant: str,
    all_features: list[str],
    ranking: RandomForestFeatureSelector,
) -> list[str]:
    if variant == "all":
        return list(all_features)
    count = int(variant.removeprefix("top_"))
    if count > len(ranking.selected_feature_names_):
        raise ValueError(f"Ranking não contém top_{count}.")
    return list(ranking.selected_feature_names_[:count])


def _validate_variants(variants: Iterable[str]) -> None:
    invalid = [
        value
        for value in variants
        if value != "all" and not (value.startswith("top_") and value[4:].isdigit())
    ]
    if invalid:
        raise ValueError(f"Variantes inválidas: {invalid}")


def _serialized_size_bytes(model: Any, algorithm: str) -> int:
    with tempfile.NamedTemporaryFile(suffix=".keras" if algorithm == "lstm" else ".joblib") as handle:
        if algorithm == "lstm":
            model.save(handle.name, overwrite=True)
        else:
            joblib.dump(model, handle.name)
        return Path(handle.name).stat().st_size


def _selector_state_sha256(selector: RandomForestFeatureSelector) -> str:
    data = json.dumps(selector.to_dict(), sort_keys=True, separators=(",", ":"))
    return sha256(data.encode("utf-8")).hexdigest()


def _names_sha256(names: list[str]) -> str:
    return sha256("\n".join(names).encode("utf-8")).hexdigest()


def _record_ids_sha256(ids: np.ndarray) -> str:
    return sha256(np.asarray(ids, dtype="<i8").tobytes()).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_parquet(frame: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        frame.to_parquet(temporary, index=False)
        if pq.ParquetFile(temporary).metadata.num_rows != len(frame):
            raise RuntimeError("Parquet temporário possui contagem divergente.")
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_json(payload: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=destination.parent, delete=False
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


def _parse_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--fold-dir", default=str(DEFAULT_FOLD_DIR))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--algorithms", default=",".join(DEFAULT_ALGORITHMS))
    parser.add_argument("--variants", default=",".join(DEFAULT_VARIANTS))
    parser.add_argument("--folds", default="1,2,3")
    parser.add_argument("--selector-n-estimators", type=int, default=100)
    parser.add_argument("--selector-n-jobs", type=int, default=2)
    parser.add_argument("--rf-n-estimators", type=int, default=config.RF_N_ESTIMATORS)
    parser.add_argument("--lstm-epochs", type=int, default=config.LSTM_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=25_000)
    parser.add_argument("--skip-prepare", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    folds = tuple(int(value) for value in _parse_csv(args.folds))
    if not args.skip_prepare:
        prepare_experiment_fold_caches(
            raw_dir=args.raw_dir,
            fold_dir=args.fold_dir,
            cache_dir=args.cache_dir,
            report_dir=args.report_dir,
            folds=folds,
            selector_n_estimators=args.selector_n_estimators,
            selector_n_jobs=args.selector_n_jobs,
            overwrite=args.overwrite,
        )
    summary = run_development_experiments(
        cache_dir=args.cache_dir,
        report_dir=args.report_dir,
        algorithms=_parse_csv(args.algorithms),
        variants=_parse_csv(args.variants),
        folds=folds,
        batch_size=args.batch_size,
        rf_n_estimators=args.rf_n_estimators,
        lstm_epochs=args.lstm_epochs,
        overwrite=args.overwrite,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
