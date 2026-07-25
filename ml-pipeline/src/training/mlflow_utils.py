"""Infraestrutura compartilhada de rastreamento MLflow."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import mlflow

import config

MLFLOW_EXPERIMENT_PREFIX = "ic-ml-cybersecurity"


def tracking_dir(tracking_uri: str | None = None) -> Path:
    """Resolve e cria o diretório local usado pelo MLflow."""
    uri = tracking_uri or config.MLFLOW_TRACKING_URI
    path = Path(uri)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def experiment_name(model_type: str) -> str:
    """Retorna o nome padronizado do experimento por tipo de modelo."""
    return f"{MLFLOW_EXPERIMENT_PREFIX}-{model_type}"


def setup_mlflow_tracking(
    model_type: str,
    flavor: Literal["sklearn", "tensorflow"] = "sklearn",
    tracking_uri: str | None = None,
) -> str:
    """Configura tracking local, experimento nomeado e autolog da flavor."""
    uri_path = tracking_dir(tracking_uri)
    mlflow.set_tracking_uri(str(uri_path))
    name = experiment_name(model_type)
    mlflow.set_experiment(name)

    if flavor == "sklearn":
        mlflow.sklearn.autolog()
    elif flavor == "tensorflow":
        mlflow.tensorflow.autolog()
    else:
        raise ValueError(f"Flavor MLflow invalida: {flavor}")

    return name
