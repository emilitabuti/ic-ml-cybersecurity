"""Testes dos controles de reprodutibilidade do pipeline temporal."""

import random

import numpy as np
import pytest


class TestConfigReproducibility:
    """Valida as constantes e variáveis de configuração em config.py."""

    def test_config_random_seed_is_42(self) -> None:
        """RANDOM_SEED deve ser 42 — constante científica do projeto."""
        import config

        assert config.RANDOM_SEED == 42

    def test_config_window_size_exists_and_is_int(self) -> None:
        """WINDOW_SIZE deve existir e ser inteiro."""
        import config

        assert hasattr(config, "WINDOW_SIZE")
        assert isinstance(config.WINDOW_SIZE, int)
        assert config.WINDOW_SIZE > 0

    def test_config_confidence_threshold_exists_and_is_float(self) -> None:
        """CONFIDENCE_THRESHOLD deve existir e ser float no intervalo [0, 1]."""
        import config

        assert hasattr(config, "CONFIDENCE_THRESHOLD")
        assert isinstance(config.CONFIDENCE_THRESHOLD, float)
        assert 0.0 <= config.CONFIDENCE_THRESHOLD <= 1.0

    def test_config_model_artifact_path_exists_and_is_str(self) -> None:
        """MODEL_ARTIFACT_PATH deve existir e apontar para o artefato canônico."""
        import config

        assert config.MODEL_ARTIFACT_PATH == "models/model_rf_temporal_v2.pkl"


class TestSetGlobalSeed:
    """Valida a função set_global_seed do módulo src.utils.seed."""

    def test_set_global_seed_importable(self) -> None:
        """Função set_global_seed deve ser importável sem erros."""
        from src.utils.seed import set_global_seed

        assert callable(set_global_seed)

    def test_set_global_seed_returns_none(self) -> None:
        """set_global_seed deve executar sem exceções e retornar None."""
        from src.utils.seed import set_global_seed

        result = set_global_seed(42)
        assert result is None

    def test_set_global_seed_accepts_any_int(self) -> None:
        """set_global_seed deve aceitar qualquer seed inteiro sem erros."""
        from src.utils.seed import set_global_seed

        for seed in [0, 1, 42, 100, 9999]:
            set_global_seed(seed)  # não deve lançar exceção

    def test_set_global_seed_sets_pythonhashseed(self) -> None:
        """PYTHONHASHSEED deve ser definido como string do seed."""
        import os

        from src.utils.seed import set_global_seed

        set_global_seed(42)
        assert os.environ.get("PYTHONHASHSEED") == "42"


class TestNumpyReproducibility:
    """Valida reprodutibilidade com numpy."""

    def test_numpy_reproducibility_with_same_seed(self) -> None:
        """Arrays gerados com o mesmo seed devem ser idênticos."""
        from src.utils.seed import set_global_seed

        set_global_seed(42)
        arr1 = np.random.rand(100)

        set_global_seed(42)
        arr2 = np.random.rand(100)

        np.testing.assert_array_equal(arr1, arr2)

    def test_numpy_different_seeds_produce_different_arrays(self) -> None:
        """Arrays gerados com seeds diferentes devem ser distintos."""
        from src.utils.seed import set_global_seed

        set_global_seed(42)
        arr1 = np.random.rand(100)

        set_global_seed(99)
        arr2 = np.random.rand(100)

        assert not np.array_equal(arr1, arr2)


class TestRandomModuleReproducibility:
    """Valida reprodutibilidade com o módulo random do Python."""

    def test_random_reproducibility_with_same_seed(self) -> None:
        """Sequências do módulo random devem ser idênticas com o mesmo seed."""
        from src.utils.seed import set_global_seed

        set_global_seed(42)
        seq1 = [random.random() for _ in range(50)]

        set_global_seed(42)
        seq2 = [random.random() for _ in range(50)]

        assert seq1 == seq2

    def test_random_different_seeds_produce_different_sequences(self) -> None:
        """Seeds diferentes devem gerar sequências distintas."""
        from src.utils.seed import set_global_seed

        set_global_seed(42)
        seq1 = [random.random() for _ in range(50)]

        set_global_seed(99)
        seq2 = [random.random() for _ in range(50)]

        assert seq1 != seq2


class TestSklearnReproducibility:
    """Valida reprodutibilidade com sklearn usando RANDOM_SEED."""

    def test_sklearn_shuffle_reproducibility(self) -> None:
        """Embaralhamento com sklearn deve ser idêntico com o mesmo seed."""
        from sklearn.utils import shuffle

        from config import RANDOM_SEED

        data = list(range(200))

        shuffled1 = shuffle(data, random_state=RANDOM_SEED)
        shuffled2 = shuffle(data, random_state=RANDOM_SEED)

        assert list(shuffled1) == list(shuffled2)

    def test_canonical_model_hyperparameters_are_fixed(self) -> None:
        """Os hiperparâmetros vencedores devem permanecer explícitos."""
        import config

        assert config.RF_N_ESTIMATORS == 100
        assert config.RF_MAX_DEPTH == "20"
        assert config.FEATURE_SELECTION_TOP_N == 30
