"""Utilitários de reprodutibilidade científica.

Este módulo centraliza a inicialização do seed global para garantir que
todos os experimentos sejam 100% reprodutíveis em qualquer máquina.
"""
import logging
import os
import random

import numpy as np

logger = logging.getLogger(__name__)


def set_global_seed(seed: int) -> None:
    """Aplica seed global em todas as bibliotecas de aleatoriedade.

    Deve ser chamado no início de qualquer script de treino ou avaliação,
    antes de qualquer operação aleatória.

    Args:
        seed: Valor inteiro do seed (recomendado: config.RANDOM_SEED = 42).
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)

    try:
        import tensorflow as tf  # type: ignore[import-untyped]
        tf.random.set_seed(seed)
        logger.info("TensorFlow seed configurado: %d", seed)
    except ImportError:
        pass  # TensorFlow é opcional neste ambiente

    logger.info("Global seed set to %d", seed)
