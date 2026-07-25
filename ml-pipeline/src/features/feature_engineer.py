"""Transformações de feature engineering para janelas deslizantes."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Optional

import numpy as np

import config

logger = logging.getLogger(__name__)

ALLOWED_WINDOW_SIZES = {5, 10, 20}


@dataclass(frozen=True)
class SlidingWindowResult:
    """Resultado da transformação em sliding window."""

    X: np.ndarray
    y: np.ndarray
    window_indices: np.ndarray

    def flatten(self) -> "SlidingWindowResult":
        """Retorna representação 2D para modelos tabulares."""
        if self.X.ndim == 2:
            return self
        if self.X.ndim != 3:
            raise ValueError("X deve ser 3D para achatar janelas sequenciais.")
        n_windows = self.X.shape[0]
        return SlidingWindowResult(
            X=self.X.reshape(n_windows, -1),
            y=self.y.copy(),
            window_indices=self.window_indices.copy(),
        )


def create_sliding_windows(
    X: np.ndarray,
    y: np.ndarray,
    window_size: Optional[int] = None,
    flatten: bool = False,
    indices: np.ndarray | None = None,
) -> SlidingWindowResult:
    """Cria janelas deslizantes consecutivas para um único split de dados.

    Args:
        X: Features com shape (n_samples, n_features).
        y: Labels com shape (n_samples,).
        window_size: Tamanho N da janela. Default: config.WINDOW_SIZE.
        flatten: Se True, retorna X achatado para RF/DT.
        indices: Índices originais das linhas de X/y para auditoria anti-leakage.

    Returns:
        SlidingWindowResult com X, y e window_indices.
    """
    X_array = np.asarray(X)
    y_array = np.asarray(y)
    resolved_window_size = _resolve_window_size(window_size)
    sample_indices = _resolve_indices(indices, X_array.shape[0])
    _validate_window_input(X_array, y_array, sample_indices, resolved_window_size)

    n_windows = X_array.shape[0] - resolved_window_size + 1
    X_windows = np.stack(
        [X_array[start : start + resolved_window_size] for start in range(n_windows)]
    )
    y_windows = y_array[resolved_window_size - 1 :]
    window_indices = np.stack(
        [
            sample_indices[start : start + resolved_window_size]
            for start in range(n_windows)
        ]
    )

    result = SlidingWindowResult(
        X=X_windows,
        y=y_windows,
        window_indices=window_indices,
    )
    if flatten:
        result = result.flatten()

    logger.info(
        "Sliding window criada: samples=%d | windows=%d | window_size=%d | flatten=%s",
        X_array.shape[0],
        n_windows,
        resolved_window_size,
        flatten,
    )
    return result


def create_train_test_windows(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    window_size: Optional[int] = None,
    train_indices: np.ndarray | None = None,
    test_indices: np.ndarray | None = None,
    flatten: bool = False,
) -> tuple[SlidingWindowResult, SlidingWindowResult]:
    """Aplica sliding window separadamente em treino e teste."""
    resolved_window_size = _resolve_window_size(window_size)
    train_windows = create_sliding_windows(
        X_train,
        y_train,
        window_size=resolved_window_size,
        flatten=flatten,
        indices=train_indices,
    )
    test_windows = create_sliding_windows(
        X_test,
        y_test,
        window_size=resolved_window_size,
        flatten=flatten,
        indices=test_indices,
    )
    return train_windows, test_windows


def _resolve_window_size(window_size: Optional[int]) -> int:
    resolved = config.WINDOW_SIZE if window_size is None else window_size
    if resolved not in ALLOWED_WINDOW_SIZES:
        raise ValueError(
            "WINDOW_SIZE deve ser um dos valores permitidos: 5, 10 ou 20. "
            f"Recebido: {resolved}."
        )
    return int(resolved)


def _resolve_indices(indices: np.ndarray | None, n_samples: int) -> np.ndarray:
    if indices is None:
        return np.arange(n_samples)
    return np.asarray(indices)


def _validate_window_input(
    X: np.ndarray,
    y: np.ndarray,
    indices: np.ndarray,
    window_size: int,
) -> None:
    if X.ndim != 2:
        raise ValueError("X deve ser 2D, com shape (n_samples, n_features).")
    if y.ndim != 1:
        raise ValueError("y deve ser 1D, com shape (n_samples,).")
    if X.shape[0] != y.shape[0]:
        raise ValueError("X e y devem ter o mesmo número de amostras.")
    if indices.ndim != 1 or indices.shape[0] != X.shape[0]:
        raise ValueError("indices deve ser 1D e ter o mesmo número de amostras de X.")
    if X.shape[0] < window_size:
        raise ValueError(
            "window_size deve ser menor ou igual ao número de amostras do split."
        )
