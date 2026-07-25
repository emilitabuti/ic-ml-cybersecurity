"""Validação anti-leakage do pipeline de features — Story 2.3."""
import json
from pathlib import Path

import numpy as np


def _make_traceable_dataset() -> tuple[np.ndarray, np.ndarray]:
    """Dataset sintético com primeira coluna como identificador original."""
    rng = np.random.default_rng(seed=42)
    n_samples = 120
    original_ids = np.arange(n_samples, dtype=float).reshape(-1, 1)
    signal = rng.normal(size=(n_samples, 1))
    noise = rng.normal(size=(n_samples, 4))
    X = np.hstack([original_ids, signal, noise])
    y = (signal[:, 0] > np.median(signal[:, 0])).astype(int)
    return X, y


class TestFeatureEngineeringAntiLeakage:
    """AC #1 — nenhum índice de teste deve aparecer em janelas do treino."""

    def test_test_indices_never_appear_in_train_windows(self) -> None:
        """Pipeline split -> selection -> windows deve preservar separação."""
        from src.data.data_splitter import split_train_test
        from src.features.feature_engineer import create_train_test_windows
        from src.features.feature_selector import RandomForestFeatureSelector

        X, y = _make_traceable_dataset()
        X_train, X_test, y_train, y_test = split_train_test(X, y, test_size=0.25)

        train_indices = X_train[:, 0].astype(int)
        test_indices = X_test[:, 0].astype(int)
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        selector = RandomForestFeatureSelector(feature_names=feature_names, top_n=3)

        X_train_selected = selector.fit_transform(X_train, y_train)
        X_test_selected = selector.transform(X_test)
        train_windows, test_windows = create_train_test_windows(
            X_train_selected,
            y_train,
            X_test_selected,
            y_test,
            window_size=5,
            train_indices=train_indices,
            test_indices=test_indices,
        )

        train_window_indices = set(train_windows.window_indices.reshape(-1).tolist())
        test_index_set = set(test_indices.tolist())
        test_window_indices = set(test_windows.window_indices.reshape(-1).tolist())

        assert train_window_indices.isdisjoint(test_index_set)
        assert train_window_indices.isdisjoint(test_window_indices)


class TestFeatureSelectionTrainOnly:
    """AC #2 e #3 — seleção calculada só com treino e transform sem refit."""

    def test_feature_selection_artifact_records_train_only_metadata(
        self,
        tmp_path: Path,
    ) -> None:
        """Artefato deve registrar contagem de treino, não treino + teste."""
        from src.features.feature_selector import RandomForestFeatureSelector

        X, y = _make_traceable_dataset()
        X_train = X[:80]
        y_train = y[:80]
        X_test = X[80:]
        artifact_path = tmp_path / "feature_selection.json"
        selector = RandomForestFeatureSelector(
            feature_names=[f"feature_{i}" for i in range(X.shape[1])],
            top_n=2,
            artifact_path=artifact_path,
        )

        selector.fit(X_train, y_train)
        selector.transform(X_test)
        selector.save()

        payload = json.loads(artifact_path.read_text(encoding="utf-8"))

        assert payload["n_training_samples"] == len(X_train)
        assert payload["n_training_samples"] != len(X_train) + len(X_test)
        assert payload["n_input_features"] == X_train.shape[1]
        assert len(payload["feature_importances"]) == X_train.shape[1]
        assert payload["selected_indices"] == selector.selected_indices_.tolist()

    def test_transforming_test_data_never_recomputes_feature_importances(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        """Após fit em treino, transform(X_test) não deve instanciar RF."""
        from src.features import feature_selector as feature_selector_module
        from src.features.feature_selector import RandomForestFeatureSelector

        X, y = _make_traceable_dataset()
        X_train = X[:80]
        y_train = y[:80]
        X_test = X[80:]
        selector = RandomForestFeatureSelector(
            feature_names=[f"feature_{i}" for i in range(X.shape[1])],
            top_n=2,
            artifact_path=tmp_path / "feature_selection.json",
        )
        selector.fit(X_train, y_train)
        feature_importances_before = selector.feature_importances_.copy()
        selected_indices_before = selector.selected_indices_.copy()

        def fail_if_classifier_is_created(*args, **kwargs):
            raise AssertionError("transform(X_test) não deve recalcular Random Forest")

        monkeypatch.setattr(
            feature_selector_module,
            "RandomForestClassifier",
            fail_if_classifier_is_created,
        )

        X_test_selected = selector.transform(X_test)

        assert X_test_selected.shape == (len(X_test), 2)
        np.testing.assert_allclose(selector.feature_importances_, feature_importances_before)
        np.testing.assert_array_equal(selector.selected_indices_, selected_indices_before)
