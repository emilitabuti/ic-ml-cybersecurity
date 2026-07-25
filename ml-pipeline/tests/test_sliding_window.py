"""Testes da transformação em sliding window — Story 2.2."""
import numpy as np
import pytest


@pytest.fixture
def sequential_data() -> tuple[np.ndarray, np.ndarray]:
    """Dataset simples em que cada linha é fácil de rastrear."""
    X = np.arange(30 * 3, dtype=float).reshape(30, 3)
    y = np.arange(30, dtype=int) % 2
    return X, y


class TestCreateSlidingWindows:
    """AC #1 e #2 — janelas consecutivas e label do último registro."""

    def test_creates_consecutive_windows(self, sequential_data: tuple[np.ndarray, np.ndarray]) -> None:
        """Cada janela deve conter N registros consecutivos."""
        from src.features.feature_engineer import create_sliding_windows

        X, y = sequential_data
        result = create_sliding_windows(X, y, window_size=5)

        assert result.X.shape == (26, 5, 3)
        np.testing.assert_array_equal(result.X[0], X[0:5])
        np.testing.assert_array_equal(result.X[1], X[1:6])
        np.testing.assert_array_equal(result.X[-1], X[25:30])

    def test_window_label_is_last_record_label(
        self,
        sequential_data: tuple[np.ndarray, np.ndarray],
    ) -> None:
        """O label da janela deve ser o label do último item."""
        from src.features.feature_engineer import create_sliding_windows

        X, y = sequential_data
        result = create_sliding_windows(X, y, window_size=5)

        np.testing.assert_array_equal(result.y, y[4:])
        assert result.y[0] == y[4]
        assert result.y[-1] == y[-1]

    def test_uses_config_window_size_by_default(
        self,
        sequential_data: tuple[np.ndarray, np.ndarray],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Sem window_size explícito, deve usar config.WINDOW_SIZE."""
        import config
        from src.features.feature_engineer import create_sliding_windows

        X, y = sequential_data
        monkeypatch.setattr(config, "WINDOW_SIZE", 10)

        result = create_sliding_windows(X, y)

        assert result.X.shape == (21, 10, 3)


class TestSlidingWindowShapes:
    """AC #4 — shape sequencial para LSTM e achatado para RF/DT."""

    def test_lstm_shape_for_window_size_10(self, sequential_data: tuple[np.ndarray, np.ndarray]) -> None:
        """Formato padrão deve ser 3D: (N, window_size, num_features)."""
        from src.features.feature_engineer import create_sliding_windows

        X, y = sequential_data
        result = create_sliding_windows(X, y, window_size=10)

        assert result.X.shape == (21, 10, 3)

    def test_tabular_shape_for_window_size_10(
        self,
        sequential_data: tuple[np.ndarray, np.ndarray],
    ) -> None:
        """Formato achatado deve ser 2D: (N, window_size * num_features)."""
        from src.features.feature_engineer import create_sliding_windows

        X, y = sequential_data
        result = create_sliding_windows(X, y, window_size=10, flatten=True)

        assert result.X.shape == (21, 30)
        np.testing.assert_array_equal(result.X[0], X[0:10].reshape(-1))

    def test_result_flatten_preserves_labels_and_indices(
        self,
        sequential_data: tuple[np.ndarray, np.ndarray],
    ) -> None:
        """SlidingWindowResult.flatten() deve preservar y e window_indices."""
        from src.features.feature_engineer import create_sliding_windows

        X, y = sequential_data
        indices = np.arange(100, 130)
        result = create_sliding_windows(X, y, window_size=5, indices=indices)
        flattened = result.flatten()

        assert flattened.X.shape == (26, 15)
        np.testing.assert_array_equal(flattened.y, result.y)
        np.testing.assert_array_equal(flattened.window_indices, result.window_indices)


class TestTrainTestSlidingWindows:
    """AC #3 — treino e teste transformados separadamente."""

    def test_train_and_test_windows_keep_disjoint_original_indices(self) -> None:
        """Índices originais de teste não devem aparecer nas janelas do treino."""
        from src.features.feature_engineer import create_train_test_windows

        X_train = np.arange(20 * 2, dtype=float).reshape(20, 2)
        y_train = np.zeros(20, dtype=int)
        X_test = np.arange(15 * 2, dtype=float).reshape(15, 2) + 1000
        y_test = np.ones(15, dtype=int)
        train_indices = np.arange(0, 20)
        test_indices = np.arange(100, 115)

        train_windows, test_windows = create_train_test_windows(
            X_train,
            y_train,
            X_test,
            y_test,
            window_size=5,
            train_indices=train_indices,
            test_indices=test_indices,
        )

        assert set(train_windows.window_indices.reshape(-1)).isdisjoint(
            set(test_windows.window_indices.reshape(-1))
        )
        np.testing.assert_array_equal(train_windows.window_indices[0], np.arange(0, 5))
        np.testing.assert_array_equal(test_windows.window_indices[0], np.arange(100, 105))

    def test_train_test_flatten_applies_to_both_sets(self) -> None:
        """flatten=True deve achatar treino e teste sem misturar conjuntos."""
        from src.features.feature_engineer import create_train_test_windows

        X_train = np.arange(20 * 2, dtype=float).reshape(20, 2)
        y_train = np.zeros(20, dtype=int)
        X_test = np.arange(15 * 2, dtype=float).reshape(15, 2)
        y_test = np.ones(15, dtype=int)

        train_windows, test_windows = create_train_test_windows(
            X_train,
            y_train,
            X_test,
            y_test,
            window_size=5,
            flatten=True,
        )

        assert train_windows.X.shape == (16, 10)
        assert test_windows.X.shape == (11, 10)


class TestSlidingWindowValidation:
    """Validações de tamanho de janela e inputs."""

    def test_invalid_window_size_raises_value_error(
        self,
        sequential_data: tuple[np.ndarray, np.ndarray],
    ) -> None:
        """WINDOW_SIZE deve estar entre os valores experimentais permitidos."""
        from src.features.feature_engineer import create_sliding_windows

        X, y = sequential_data
        with pytest.raises(ValueError, match="WINDOW_SIZE"):
            create_sliding_windows(X, y, window_size=7)

    def test_window_size_larger_than_dataset_raises_value_error(
        self,
        sequential_data: tuple[np.ndarray, np.ndarray],
    ) -> None:
        """Não deve criar dataset vazio silenciosamente."""
        from src.features.feature_engineer import create_sliding_windows

        X, y = sequential_data
        with pytest.raises(ValueError, match="menor ou igual"):
            create_sliding_windows(X[:4], y[:4], window_size=5)

    def test_indices_length_must_match_samples(
        self,
        sequential_data: tuple[np.ndarray, np.ndarray],
    ) -> None:
        """Índices originais devem cobrir todas as amostras."""
        from src.features.feature_engineer import create_sliding_windows

        X, y = sequential_data
        with pytest.raises(ValueError, match="indices"):
            create_sliding_windows(X, y, window_size=5, indices=np.arange(10))
