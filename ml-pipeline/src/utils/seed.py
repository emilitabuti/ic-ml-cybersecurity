"""
É para garantir que todos os experimentos sejam 100% reprodutíveis em qualquer máquina.
"""
import logging
import os
import random

import numpy as np

logger = logging.getLogger(__name__)


def set_global_seed(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)

    try:
        import tensorflow as tf  # type: ignore[import-untyped]
        tf.random.set_seed(seed)
        logger.info("TensorFlow seed configurado: %d", seed)
    except ImportError:
        pass  # TensorFlow é opcional

    logger.info("Global seed set to %d", seed)
