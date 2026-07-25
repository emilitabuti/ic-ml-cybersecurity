"""Preparação dos dados model-ready para treino com k-fold."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

import config
from src.data.data_loader import _NON_FEATURE_COLS, load_dataset
from src.features.feature_engineer import create_sliding_windows


@dataclass(frozen=True)
class PreparedDataset:
    """Dataset em formato sequencial e tabular para comparação de modelos."""

    X_sequential: np.ndarray
    X_tabular: np.ndarray
    y: np.ndarray
    attack_types: np.ndarray
    feature_names: list[str]
    window_size: int


def prepare_windowed_binary_dataset(
    dataset: str = "cic",
    window_size: int | None = None,
) -> PreparedDataset:
    """Carrega o parquet binário e cria janelas para LSTM e RF/DT."""
    df = load_dataset(dataset=dataset, task="binary")
    feature_cols = [column for column in df.columns if column not in _NON_FEATURE_COLS]
    X = df[feature_cols].to_numpy(dtype=np.float64)
    y = df["Binary_Label"].to_numpy(dtype=int)
    attack_types = _resolve_attack_types(df, y)
    return prepare_windowed_binary_arrays(
        X=X,
        y=y,
        attack_types=attack_types,
        feature_names=feature_cols,
        window_size=window_size,
    )


def prepare_windowed_binary_arrays(
    X: np.ndarray,
    y: np.ndarray,
    attack_types: Sequence[str] | np.ndarray | None = None,
    feature_names: list[str] | None = None,
    window_size: int | None = None,
) -> PreparedDataset:
    """Cria representações 3D e achatada a partir de arrays em memória."""
    resolved_window_size = int(window_size or config.WINDOW_SIZE)
    X_array = np.asarray(X, dtype=np.float64)
    y_array = np.asarray(y, dtype=int)
    resolved_attack_types = _resolve_attack_array(attack_types, y_array)

    sequential = create_sliding_windows(
        X_array,
        y_array,
        window_size=resolved_window_size,
        flatten=False,
    )
    tabular = sequential.flatten()
    window_attack_types = resolved_attack_types[resolved_window_size - 1 :]

    names = feature_names or [f"feature_{index}" for index in range(X_array.shape[1])]
    return PreparedDataset(
        X_sequential=sequential.X,
        X_tabular=tabular.X,
        y=sequential.y,
        attack_types=window_attack_types.astype(str),
        feature_names=list(names),
        window_size=resolved_window_size,
    )


def _resolve_attack_types(df: pd.DataFrame, y: np.ndarray) -> np.ndarray:
    if "Attack_Type" in df.columns:
        return df["Attack_Type"].fillna("BENIGN").astype(str).to_numpy()
    if "label" in df.columns:
        return df["label"].fillna("BENIGN").astype(str).to_numpy()
    return _resolve_attack_array(None, y)


def _resolve_attack_array(
    attack_types: Sequence[str] | np.ndarray | None,
    y: np.ndarray,
) -> np.ndarray:
    if attack_types is None:
        return np.where(y == 1, "Attack", "BENIGN").astype(str)
    attack_array = np.asarray(attack_types).astype(str)
    if attack_array.shape[0] != y.shape[0]:
        raise ValueError("attack_types deve ter o mesmo numero de amostras de y.")
    return attack_array
