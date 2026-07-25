"""Carregador de dados pré-processados para o pipeline de ML.

Ponto de entrada principal para consumir os datasets preparados por Caroline.
Lê os arquivos parquet de `data/processed/` e retorna arrays X, y prontos
para feature engineering.

Uso típico:
    from src.data.data_loader import load_binary_dataset
    from config import RANDOM_SEED

    X, y = load_binary_dataset(dataset="cic")
"""
import logging
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Caminhos dos datasets model-ready ─────────────────────────────────────────

_PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"

_PATHS = {
    "cic": {
        "binary": _PROCESSED_DIR / "cic_ids2017_model_ready_binary.parquet",
        "attacktype": _PROCESSED_DIR / "cic_ids2017_model_ready_attacktype.parquet",
    },
    "unsw": {
        "binary": _PROCESSED_DIR / "unsw_nb15_model_ready_binary.parquet",
        "attacktype": _PROCESSED_DIR / "unsw_nb15_model_ready_attacktype.parquet",
    },
}

DatasetName = Literal["cic", "unsw"]
TaskName = Literal["binary", "attacktype"]

# Colunas que não são features de entrada
# srcip/dstip são identificadores de rede (não features de tráfego) — mantê-los
# causaria vazamento de dados, pois o modelo memorizaria IPs vistos no treino
# em vez de aprender padrões de tráfego generalizáveis.
_NON_FEATURE_COLS = {
    "Binary_Label",
    "Attack_Type",
    "Attack_Type_ID",
    "label",
    "source_file",
    "srcip",
    "dstip",
}


def load_dataset(
    dataset: DatasetName = "cic",
    task: TaskName = "binary",
) -> pd.DataFrame:
    """Carrega o dataset model-ready como DataFrame.

    Args:
        dataset: Nome do dataset — "cic" (CIC-IDS2017) ou "unsw" (UNSW-NB15).
        task: Tipo de tarefa — "binary" ou "attacktype".

    Returns:
        DataFrame completo com features + coluna(s) alvo.

    Raises:
        FileNotFoundError: Se o arquivo parquet não existir em data/processed/.
        ValueError: Se dataset ou task forem inválidos.
    """
    if dataset not in _PATHS:
        raise ValueError(f"Dataset inválido: '{dataset}'. Opções: {list(_PATHS.keys())}")
    if task not in _PATHS[dataset]:
        raise ValueError(f"Task inválida: '{task}'. Opções: binary, attacktype")

    path = _PATHS[dataset][task]

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset não encontrado: {path}\n"
            "Execute o pipeline de pré-processamento de Caroline primeiro:\n"
            "  python -m src.data.pipeline.collector\n"
            "  python -m src.data.pipeline.cleaner\n"
            "  python -m src.data.pipeline.scaler\n"
            "  python -m src.data.pipeline.preprocessor"
        )

    logger.info("Carregando dataset %s (%s): %s", dataset.upper(), task, path)
    df = pd.read_parquet(path)
    logger.info("Carregado — linhas: %d | colunas: %d", df.shape[0], df.shape[1])
    return df


def load_binary_dataset(
    dataset: DatasetName = "cic",
) -> tuple[np.ndarray, np.ndarray]:
    """Carrega X e y para classificação binária (Benigno vs Ataque).

    Args:
        dataset: Nome do dataset — "cic" ou "unsw".

    Returns:
        Tupla (X, y) onde:
            X — array de features (float64), shape (n_samples, n_features)
            y — array de labels binários (int), shape (n_samples,)
    """
    df = load_dataset(dataset=dataset, task="binary")

    feature_cols = [c for c in df.columns if c not in _NON_FEATURE_COLS]
    X = df[feature_cols].values.astype(np.float64)
    y = df["Binary_Label"].values.astype(int)

    logger.info("X shape: %s | y shape: %s | classe 0: %d | classe 1: %d",
                X.shape, y.shape, (y == 0).sum(), (y == 1).sum())
    return X, y


def load_attacktype_dataset(
    dataset: DatasetName = "cic",
) -> tuple[np.ndarray, np.ndarray]:
    """Carrega X e y para classificação multi-classe do tipo de ataque.

    Contém apenas amostras maliciosas (Binary_Label = 1).

    Args:
        dataset: Nome do dataset — "cic" ou "unsw".

    Returns:
        Tupla (X, y) onde:
            X — array de features (float64), shape (n_samples, n_features)
            y — array de IDs de tipo de ataque (int), shape (n_samples,)
    """
    df = load_dataset(dataset=dataset, task="attacktype")

    feature_cols = [c for c in df.columns if c not in _NON_FEATURE_COLS]
    X = df[feature_cols].values.astype(np.float64)
    y = df["Attack_Type_ID"].values.astype(int)

    n_classes = len(np.unique(y))
    logger.info("X shape: %s | y shape: %s | classes: %d", X.shape, y.shape, n_classes)
    return X, y


def get_feature_names(dataset: DatasetName = "cic", task: TaskName = "binary") -> list[str]:
    """Retorna a lista de nomes das features sem carregar o dataset completo.

    Lê apenas o schema do parquet (metadados) — operação de O(KB), não O(GB).

    Args:
        dataset: Nome do dataset.
        task: Tipo de tarefa.

    Returns:
        Lista de strings com os nomes das colunas de features.
    """
    if dataset not in _PATHS:
        raise ValueError(f"Dataset inválido: '{dataset}'. Opções: {list(_PATHS.keys())}")
    if task not in _PATHS[dataset]:
        raise ValueError(f"Task inválida: '{task}'. Opções: binary, attacktype")

    path = _PATHS[dataset][task]
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset não encontrado: {path}\n"
            "Execute o pipeline de pré-processamento de Caroline primeiro:\n"
            "  python -m src.data.pipeline.collector\n"
            "  python -m src.data.pipeline.cleaner\n"
            "  python -m src.data.pipeline.scaler\n"
            "  python -m src.data.pipeline.preprocessor"
        )

    import pyarrow.parquet as pq
    schema = pq.read_schema(path)
    return [c for c in schema.names if c not in _NON_FEATURE_COLS]
