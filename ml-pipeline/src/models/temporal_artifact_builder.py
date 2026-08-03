"""Empacota o Random Forest vencedor no artefato canônico de inferência."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any

import joblib

from src.features.fold_preprocessor import FoldPreprocessor
from src.models.model_serializer import (
    ARTIFACT_VERSION,
    DEFAULT_LABEL_ENCODING,
    PIPELINE_KIND,
    load_serialized_model,
)


DEFAULT_PROTOCOL = Path("reports_temporal/unsw/protocol.json")
DEFAULT_FINAL_SUMMARY = Path("reports_temporal/unsw/final_test_metrics.json")
DEFAULT_FINAL_DIR = Path("reports_temporal/unsw/final_evaluation")
DEFAULT_OUTPUT = Path("models/model_rf_temporal_v2.pkl")


def build_temporal_winner_artifact(
    *,
    protocol_path: str | Path = DEFAULT_PROTOCOL,
    final_summary_path: str | Path = DEFAULT_FINAL_SUMMARY,
    final_dir: str | Path = DEFAULT_FINAL_DIR,
    output_path: str | Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    """Empacota estados já ajustados sem ler dados ou repetir o teste."""
    protocol_file = Path(protocol_path)
    summary_file = Path(final_summary_path)
    final_root = Path(final_dir)
    output = Path(output_path)
    protocol_sha = _verify_sidecar(protocol_file)
    summary_sha = _verify_sidecar(summary_file)
    protocol = _load_json(protocol_file)
    summary = _load_json(summary_file)
    winner = protocol["overall_selected_configuration"]
    if winner != {
        "algorithm": "random_forest",
        "variant": "top_30",
        "top_n": 30,
        "reason": "Maior F1 médio entre todas as configurações de desenvolvimento.",
    }:
        raise RuntimeError("O vencedor congelado não é random_forest/top_30.")
    if summary["test_evaluation_runs"] != 1:
        raise RuntimeError("O resumo final não comprova avaliação única.")

    preprocessor_path = final_root / "preprocessor_train_validation.joblib"
    selector_path = final_root / "feature_ranking_train_validation.json"
    model_path = final_root / "models/random_forest.joblib"
    preprocessor = FoldPreprocessor.load(preprocessor_path)
    selector = _load_json(selector_path)
    selected_names = list(selector["selected_feature_names"])
    if len(selected_names) != 30:
        raise RuntimeError("Ranking final não contém exatamente top_30.")
    final_result = summary["results"]["random_forest"]
    if selected_names != final_result["feature_names"]:
        raise RuntimeError("Features do modelo divergem do ranking final.")
    model = joblib.load(model_path)
    if int(getattr(model, "n_features_in_", -1)) != 300:
        raise RuntimeError("Random Forest não possui entrada window_size*top_n = 300.")

    raw_numeric = list(preprocessor.numeric_columns_)
    raw_categorical = list(preprocessor.categorical_columns_)
    raw_names = [*raw_numeric, *raw_categorical]
    artifact = {
        "artifact_version": ARTIFACT_VERSION,
        "pipeline_kind": PIPELINE_KIND,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_type": "random_forest",
        "model_format": "sklearn_joblib",
        "model": model,
        "preprocessor_state": preprocessor.__dict__,
        "raw_feature_names": raw_names,
        "raw_numeric_feature_names": raw_numeric,
        "raw_categorical_feature_names": raw_categorical,
        "selected_feature_names": selected_names,
        "feature_names": selected_names,
        "feature_selection": {
            "method": "random_forest_importance",
            "top_n": 30,
            "fit_scope": "train+validation",
            "ranking_sha256": _file_sha256(selector_path),
        },
        "window_size": int(protocol["final_fit"]["window_size"]),
        "window_transformer": {
            "name": "sliding_window",
            "flatten": True,
            "label_strategy": "last_record",
            "boundaries_required_by_stream": ["temporal_session", "source_file"],
        },
        "classification_threshold": float(
            protocol["task"]["classification_threshold"]
        ),
        "label_encoding": DEFAULT_LABEL_ENCODING,
        "protocol_sha256": protocol_sha,
        "final_metrics_sha256": summary_sha,
        "training_environment": _load_json(
            final_root / "execution_manifest.json"
        )["actual_execution_dependency_versions"],
        "audit": {
            "preprocessor_sha256": _file_sha256(preprocessor_path),
            "selector_sha256": _file_sha256(selector_path),
            "model_sha256": _file_sha256(model_path),
            "test_evaluation_runs": 1,
            "selection_or_tuning_on_test": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        joblib.dump(artifact, temporary)
        load_serialized_model(temporary)
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()

    output_sha = _file_sha256(output)
    sidecar = output.with_suffix(output.suffix + ".sha256")
    sidecar.write_text(f"{output_sha}  {output.name}\n", encoding="utf-8")
    manifest = {
        "status": "temporal_winner_artifact_built",
        "artifact_path": str(output),
        "artifact_sha256": output_sha,
        "artifact_size_bytes": output.stat().st_size,
        "artifact_version": ARTIFACT_VERSION,
        "pipeline_kind": PIPELINE_KIND,
        "model_type": "random_forest",
        "raw_feature_count": len(raw_names),
        "selected_feature_count": len(selected_names),
        "window_size": artifact["window_size"],
        "model_input_count": int(model.n_features_in_),
        "protocol_sha256": protocol_sha,
        "final_metrics_sha256": summary_sha,
        "test_reopened": False,
    }
    manifest_path = final_root / "artifact_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def _verify_sidecar(path: Path) -> str:
    expected = path.with_suffix(path.suffix + ".sha256").read_text().split()[0]
    actual = _file_sha256(path)
    if actual != expected:
        raise RuntimeError(f"SHA-256 inválido para {path}.")
    return actual


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    manifest = build_temporal_winner_artifact()
    print(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
