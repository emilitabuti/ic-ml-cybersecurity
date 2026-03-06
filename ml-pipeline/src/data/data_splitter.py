"""Módulo de divisão train/test estratificada para o pipeline de ML.

Garante que o split ocorra ANTES de qualquer transformação
(feature selection, sliding window, normalização adicional),
prevenindo data leakage entre treino e teste.

Uso típico:
    from src.data.data_loader import load_binary_dataset
    from src.data.data_splitter import split_train_test

    X, y = load_binary_dataset(dataset="cic")
    X_train, X_test, y_train, y_test = split_train_test(X, y)
"""
import logging
from typing import Optional

import numpy as np
from sklearn.model_selection import train_test_split

import config

logger = logging.getLogger(__name__)


def split_train_test(
    X: np.ndarray,
    y: np.ndarray,
    test_size: Optional[float] = None,
    random_state: Optional[int] = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Divide dados em conjuntos de treino e teste com estratificação por label.

    IMPORTANTE: Esta função deve ser chamada ANTES de qualquer transformação
    (feature selection, sliding window, normalização adicional). Aplicar
    transformações antes do split constitui data leakage.

    Args:
        X: Array de features, shape (n_samples, n_features).
        y: Array de labels, shape (n_samples,). Usado para estratificação.
        test_size: Proporção do conjunto de teste. Default: config.TEST_SIZE (0.2).
            Deve estar no intervalo (0.0, 1.0) exclusivo.
        random_state: Seed para reprodutibilidade. Default: config.RANDOM_SEED (42).

    Returns:
        Tupla (X_train, X_test, y_train, y_test) com arrays numpy.

    Raises:
        ValueError: Se test_size estiver fora do intervalo (0.0, 1.0).

    Example:
        >>> X, y = load_binary_dataset(dataset="cic")
        >>> X_train, X_test, y_train, y_test = split_train_test(X, y)
        >>> assert len(X_train) + len(X_test) == len(X)
    """
    _test_size = test_size if test_size is not None else config.TEST_SIZE
    _random_state = random_state if random_state is not None else config.RANDOM_SEED

    if not (0.0 < _test_size < 1.0):
        raise ValueError(
            f"test_size deve estar no intervalo (0.0, 1.0), recebido: {_test_size}"
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=_test_size,
        random_state=_random_state,
        stratify=y,
    )

    logger.info(
        "Split train/test: total=%d | train=%d (%.1f%%) | test=%d (%.1f%%) | seed=%d",
        len(y),
        len(y_train),
        100 * len(y_train) / len(y),
        len(y_test),
        100 * len(y_test) / len(y),
        _random_state,
    )
    logger.info(
        "Proporção de ataques: train=%.2f%% | test=%.2f%%",
        100 * float(y_train.mean()),
        100 * float(y_test.mean()),
    )

    return X_train, X_test, y_train, y_test
