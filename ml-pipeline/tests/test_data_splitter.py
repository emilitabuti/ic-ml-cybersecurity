"""
Testes do módulo de split train/test estratificado — Story 1.4.

Valida que:
- split_train_test() retorna 4 arrays com proporções corretas (80/20)
- Dois splits com mesmo seed produzem resultados idênticos
- Estratificação preserva proporção de classes em treino e teste
- Parâmetros test_size e random_state são customizáveis
- Conjuntos de treino e teste são disjuntos (sem data leakage)
- config.TEST_SIZE existe e é float válido
"""
import numpy as np
import pytest


@pytest.fixture
def synthetic_binary_data() -> tuple:
    """Dataset sintético com 1000 amostras — 70% benigno, 30% ataque."""
    n = 1000
    X = np.arange(n * 10, dtype=float).reshape(n, 10)
    y = np.zeros(n, dtype=int)
    y[700:] = 1  # 300 ataques
    return X, y


class TestSplitTrainTestBasic:
    """AC #1 — split retorna 4 arrays com proporções corretas."""

    def test_returns_four_arrays(self, synthetic_binary_data: tuple) -> None:
        """split_train_test deve retornar exatamente 4 arrays."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        result = split_train_test(X, y)
        assert len(result) == 4

    def test_total_samples_preserved(self, synthetic_binary_data: tuple) -> None:
        """Soma de treino + teste deve igualar total de amostras."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        X_train, X_test, y_train, y_test = split_train_test(X, y)
        assert len(X_train) + len(X_test) == len(X)
        assert len(y_train) + len(y_test) == len(y)

    def test_default_split_80_20(self, synthetic_binary_data: tuple) -> None:
        """Proporção padrão deve ser 80% treino / 20% teste."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        X_train, X_test, y_train, y_test = split_train_test(X, y)
        assert len(X_test) == pytest.approx(len(X) * 0.2, abs=2)
        assert len(X_train) == pytest.approx(len(X) * 0.8, abs=2)

    def test_x_and_y_shapes_consistent(self, synthetic_binary_data: tuple) -> None:
        """X e y devem ter o mesmo número de amostras em cada split."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        X_train, X_test, y_train, y_test = split_train_test(X, y)
        assert X_train.shape[0] == y_train.shape[0]
        assert X_test.shape[0] == y_test.shape[0]


class TestSplitReproducibility:
    """AC #2 — reprodutibilidade com mesmo seed."""

    def test_same_seed_produces_identical_splits(self, synthetic_binary_data: tuple) -> None:
        """Dois splits com mesmo seed devem ser idênticos."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        X_train_1, X_test_1, y_train_1, y_test_1 = split_train_test(X, y, random_state=42)
        X_train_2, X_test_2, y_train_2, y_test_2 = split_train_test(X, y, random_state=42)

        np.testing.assert_array_equal(X_train_1, X_train_2)
        np.testing.assert_array_equal(X_test_1, X_test_2)
        np.testing.assert_array_equal(y_train_1, y_train_2)
        np.testing.assert_array_equal(y_test_1, y_test_2)

    def test_different_seeds_produce_different_splits(self, synthetic_binary_data: tuple) -> None:
        """Seeds diferentes devem produzir splits diferentes."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        _, X_test_1, _, _ = split_train_test(X, y, random_state=42)
        _, X_test_2, _, _ = split_train_test(X, y, random_state=99)

        assert not np.array_equal(X_test_1, X_test_2)

    def test_uses_config_random_seed_by_default(self, synthetic_binary_data: tuple) -> None:
        """Sem argumento, deve usar config.RANDOM_SEED."""
        import config
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        X_train_default, X_test_default, _, _ = split_train_test(X, y)
        X_train_explicit, X_test_explicit, _, _ = split_train_test(
            X, y, random_state=config.RANDOM_SEED
        )

        np.testing.assert_array_equal(X_train_default, X_train_explicit)
        np.testing.assert_array_equal(X_test_default, X_test_explicit)


class TestSplitStratification:
    """AC #3 — estratificação preserva proporção de classes."""

    def test_class_proportions_preserved_in_train(self, synthetic_binary_data: tuple) -> None:
        """Proporção de ataques no treino deve ser ≈ proporção original (±2%)."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        original_ratio = y.mean()
        X_train, _, y_train, _ = split_train_test(X, y)
        train_ratio = y_train.mean()

        assert abs(train_ratio - original_ratio) < 0.02

    def test_class_proportions_preserved_in_test(self, synthetic_binary_data: tuple) -> None:
        """Proporção de ataques no teste deve ser ≈ proporção original (±2%)."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        original_ratio = y.mean()
        _, X_test, _, y_test = split_train_test(X, y)
        test_ratio = y_test.mean()

        assert abs(test_ratio - original_ratio) < 0.02

    def test_both_classes_present_in_train_and_test(self, synthetic_binary_data: tuple) -> None:
        """Ambas as classes (0 e 1) devem estar presentes em treino e teste."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        _, _, y_train, y_test = split_train_test(X, y)

        assert 0 in y_train and 1 in y_train
        assert 0 in y_test and 1 in y_test


class TestSplitCustomParams:
    """AC #1 — parâmetros customizáveis."""

    def test_custom_test_size(self, synthetic_binary_data: tuple) -> None:
        """test_size customizado deve ser respeitado."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        _, X_test, _, y_test = split_train_test(X, y, test_size=0.3)
        assert len(X_test) == pytest.approx(len(X) * 0.3, abs=2)

    def test_custom_random_state(self, synthetic_binary_data: tuple) -> None:
        """random_state customizado deve ser usado no split."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        X_train_1, _, _, _ = split_train_test(X, y, random_state=7)
        X_train_2, _, _, _ = split_train_test(X, y, random_state=7)
        np.testing.assert_array_equal(X_train_1, X_train_2)

    def test_none_params_use_config_defaults(self, synthetic_binary_data: tuple) -> None:
        """Parâmetros None devem usar valores de config."""
        import config
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        result_none = split_train_test(X, y, test_size=None, random_state=None)
        result_explicit = split_train_test(
            X, y, test_size=config.TEST_SIZE, random_state=config.RANDOM_SEED
        )
        np.testing.assert_array_equal(result_none[1], result_explicit[1])


class TestSplitNoLeakage:
    """AC #1 — garantia de ausência de data leakage entre conjuntos."""

    def test_train_test_indices_disjoint(self, synthetic_binary_data: tuple) -> None:
        """Amostras de treino e teste não devem se sobrepor."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        X_train, X_test, _, _ = split_train_test(X, y)

        # Usa a primeira coluna como identificador único (cada linha é única)
        train_ids = set(X_train[:, 0].tolist())
        test_ids = set(X_test[:, 0].tolist())

        assert train_ids.isdisjoint(test_ids), "Data leakage detectado: amostras em treino E teste"

    def test_no_duplicate_rows_between_splits(self, synthetic_binary_data: tuple) -> None:
        """Nenhuma linha de treino deve aparecer no teste."""
        from src.data.data_splitter import split_train_test

        X, y = synthetic_binary_data
        X_train, X_test, _, _ = split_train_test(X, y)

        # Converte para conjunto de tuplas para comparação
        train_set = {tuple(row) for row in X_train.tolist()}
        test_set = {tuple(row) for row in X_test.tolist()}

        assert len(train_set & test_set) == 0


class TestConfigTestSize:
    """AC #1 — config.TEST_SIZE existe e é válido."""

    def test_config_test_size_exists(self) -> None:
        """config.TEST_SIZE deve existir."""
        import config

        assert hasattr(config, "TEST_SIZE")

    def test_config_test_size_is_float(self) -> None:
        """config.TEST_SIZE deve ser float."""
        import config

        assert isinstance(config.TEST_SIZE, float)

    def test_config_test_size_in_valid_range(self) -> None:
        """config.TEST_SIZE deve estar entre 0.1 e 0.5."""
        import config

        assert 0.1 <= config.TEST_SIZE <= 0.5

    def test_config_test_size_default_is_0_2(self) -> None:
        """Valor padrão de TEST_SIZE deve ser 0.2."""
        import config

        assert config.TEST_SIZE == pytest.approx(0.2)
