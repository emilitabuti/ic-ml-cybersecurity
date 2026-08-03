"""Testes do seletor de atributos ajustado somente no treino."""
import json
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def synthetic_feature_selection_data() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Dataset sintético em que as duas primeiras features dominam o label."""
    rng = np.random.default_rng(seed=123)
    n_samples = 240
    X = rng.normal(size=(n_samples, 6))
    score = (3.0 * X[:, 0]) + (2.0 * X[:, 1]) + rng.normal(scale=0.05, size=n_samples)
    y = (score > np.median(score)).astype(int)
    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
    return X, y, feature_names


class TestRandomForestFeatureSelectorTopN:
    """AC #1, #2 e #4 — fit sobre treino, top-N e determinismo."""

    def test_selects_top_n_features_deterministically(
        self,
        synthetic_feature_selection_data: tuple[np.ndarray, np.ndarray, list[str]],
        tmp_path: Path,
    ) -> None:
        """Duas execuções com mesmo seed devem selecionar as mesmas features."""
        import config
        from src.features.feature_selector import RandomForestFeatureSelector

        X_train, y_train, feature_names = synthetic_feature_selection_data
        artifact_path = tmp_path / "feature_selection.json"

        selector_1 = RandomForestFeatureSelector(
            feature_names=feature_names,
            top_n=2,
            threshold=0.0,
            artifact_path=artifact_path,
            random_state=config.RANDOM_SEED,
        )
        selector_2 = RandomForestFeatureSelector(
            feature_names=feature_names,
            top_n=2,
            threshold=0.0,
            artifact_path=artifact_path,
            random_state=config.RANDOM_SEED,
        )

        X_selected_1 = selector_1.fit_transform(X_train, y_train)
        X_selected_2 = selector_2.fit_transform(X_train, y_train)

        assert X_selected_1.shape == (X_train.shape[0], 2)
        assert selector_1.selected_feature_names_ == selector_2.selected_feature_names_
        np.testing.assert_allclose(
            selector_1.feature_importances_, selector_2.feature_importances_
        )

    def test_uses_training_samples_only_in_fit_metadata(
        self,
        synthetic_feature_selection_data: tuple[np.ndarray, np.ndarray, list[str]],
        tmp_path: Path,
    ) -> None:
        """Metadados devem refletir apenas as amostras recebidas em fit()."""
        from src.features.feature_selector import RandomForestFeatureSelector

        X_train, y_train, feature_names = synthetic_feature_selection_data
        selector = RandomForestFeatureSelector(
            feature_names=feature_names,
            top_n=3,
            artifact_path=tmp_path / "feature_selection.json",
        )

        selector.fit(X_train[:100], y_train[:100])

        assert selector.n_training_samples_ == 100
        assert selector.n_input_features_ == X_train.shape[1]


class TestRandomForestFeatureSelectorThreshold:
    """AC #2 — seleção por threshold mínimo."""

    def test_selects_all_features_above_threshold(
        self,
        synthetic_feature_selection_data: tuple[np.ndarray, np.ndarray, list[str]],
        tmp_path: Path,
    ) -> None:
        """Com threshold, todas as selecionadas devem respeitar o mínimo."""
        from src.features.feature_selector import RandomForestFeatureSelector

        X_train, y_train, feature_names = synthetic_feature_selection_data
        selector = RandomForestFeatureSelector(
            feature_names=feature_names,
            top_n=None,
            threshold=0.05,
            artifact_path=tmp_path / "feature_selection.json",
        )

        selector.fit(X_train, y_train)

        selected_importances = selector.feature_importances_[selector.selected_indices_]
        assert len(selector.selected_indices_) >= 1
        assert np.all(selected_importances >= 0.05)

    def test_requires_at_least_one_selected_feature(
        self,
        synthetic_feature_selection_data: tuple[np.ndarray, np.ndarray, list[str]],
        tmp_path: Path,
    ) -> None:
        """Threshold alto demais deve falhar com erro descritivo."""
        from src.features.feature_selector import RandomForestFeatureSelector

        X_train, y_train, feature_names = synthetic_feature_selection_data
        selector = RandomForestFeatureSelector(
            feature_names=feature_names,
            top_n=None,
            threshold=1.1,
            artifact_path=tmp_path / "feature_selection.json",
        )

        with pytest.raises(ValueError, match="Nenhuma feature selecionada"):
            selector.fit(X_train, y_train)


class TestRandomForestFeatureSelectorPersistence:
    """AC #3 e #5 — persistência e uso consistente em treino/teste."""

    def test_persists_and_loads_selection_artifact(
        self,
        synthetic_feature_selection_data: tuple[np.ndarray, np.ndarray, list[str]],
        tmp_path: Path,
    ) -> None:
        """Artefato JSON deve permitir recarregar a seleção sem refit."""
        from src.features.feature_selector import RandomForestFeatureSelector

        X_train, y_train, feature_names = synthetic_feature_selection_data
        artifact_path = tmp_path / "feature_selection.json"
        selector = RandomForestFeatureSelector(
            feature_names=feature_names,
            top_n=2,
            artifact_path=artifact_path,
        )
        selector.fit(X_train, y_train)
        selector.save()

        loaded = RandomForestFeatureSelector.load(artifact_path)

        assert artifact_path.exists()
        assert loaded.selected_feature_names_ == selector.selected_feature_names_
        np.testing.assert_array_equal(loaded.selected_indices_, selector.selected_indices_)
        np.testing.assert_allclose(loaded.feature_importances_, selector.feature_importances_)

        X_test = X_train[:10].copy()
        np.testing.assert_array_equal(loaded.transform(X_test), selector.transform(X_test))

    def test_artifact_contains_required_metadata(
        self,
        synthetic_feature_selection_data: tuple[np.ndarray, np.ndarray, list[str]],
        tmp_path: Path,
    ) -> None:
        """JSON deve registrar parâmetros e metadados de treino."""
        import config
        from src.features.feature_selector import RandomForestFeatureSelector

        X_train, y_train, feature_names = synthetic_feature_selection_data
        artifact_path = tmp_path / "feature_selection.json"
        selector = RandomForestFeatureSelector(
            feature_names=feature_names,
            top_n=2,
            threshold=0.0,
            artifact_path=artifact_path,
        )
        selector.fit(X_train, y_train)
        selector.save()

        payload = json.loads(artifact_path.read_text(encoding="utf-8"))

        assert payload["selected_feature_names"] == selector.selected_feature_names_
        assert payload["selected_indices"] == selector.selected_indices_.tolist()
        assert len(payload["feature_importances"]) == X_train.shape[1]
        assert payload["top_n"] == 2
        assert payload["threshold"] == 0.0
        assert payload["random_state"] == config.RANDOM_SEED
        assert payload["n_training_samples"] == X_train.shape[0]
        assert payload["n_input_features"] == X_train.shape[1]

    def test_transform_does_not_refit_or_change_selection(
        self,
        synthetic_feature_selection_data: tuple[np.ndarray, np.ndarray, list[str]],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Transformar teste deve usar a seleção existente, sem recalcular importância."""
        from src.features import feature_selector as feature_selector_module
        from src.features.feature_selector import RandomForestFeatureSelector

        X_train, y_train, feature_names = synthetic_feature_selection_data
        selector = RandomForestFeatureSelector(
            feature_names=feature_names,
            top_n=2,
            artifact_path=tmp_path / "feature_selection.json",
        )
        selector.fit(X_train, y_train)
        original_selection = selector.selected_indices_.copy()

        def fail_if_classifier_is_created(*args: object, **kwargs: object) -> None:
            raise AssertionError("transform() não deve instanciar RandomForestClassifier")

        monkeypatch.setattr(
            feature_selector_module,
            "RandomForestClassifier",
            fail_if_classifier_is_created,
        )

        X_test_selected = selector.transform(X_train[:12])

        assert X_test_selected.shape == (12, 2)
        np.testing.assert_array_equal(selector.selected_indices_, original_selection)


class TestRandomForestFeatureSelectorValidation:
    """Validações de entrada e parâmetros."""

    def test_invalid_top_n_raises_value_error(self) -> None:
        """top_n deve ser positivo quando informado."""
        from src.features.feature_selector import RandomForestFeatureSelector

        with pytest.raises(ValueError, match="top_n"):
            RandomForestFeatureSelector(feature_names=["a", "b"], top_n=0)

    def test_feature_name_count_must_match_input_columns(
        self,
        synthetic_feature_selection_data: tuple[np.ndarray, np.ndarray, list[str]],
        tmp_path: Path,
    ) -> None:
        """Quantidade de nomes deve bater com colunas de X."""
        from src.features.feature_selector import RandomForestFeatureSelector

        X_train, y_train, _ = synthetic_feature_selection_data
        selector = RandomForestFeatureSelector(
            feature_names=["a", "b"],
            top_n=1,
            artifact_path=tmp_path / "feature_selection.json",
        )

        with pytest.raises(ValueError, match="feature_names"):
            selector.fit(X_train, y_train)

    def test_temporal_fit_rejects_validation_and_refit(
        self,
        synthetic_feature_selection_data: tuple[np.ndarray, np.ndarray, list[str]],
        tmp_path: Path,
    ) -> None:
        from src.features.feature_selector import RandomForestFeatureSelector

        X, y, names = synthetic_feature_selection_data
        ids = np.arange(len(y))
        with pytest.raises(ValueError, match="partition='train'"):
            RandomForestFeatureSelector(
                feature_names=names,
                top_n=2,
                artifact_path=tmp_path / "invalid.json",
            ).fit(X, y, partition="validation", record_ids=ids)

        selector = RandomForestFeatureSelector(
            feature_names=names,
            top_n=2,
            artifact_path=tmp_path / "valid.json",
        ).fit(X, y, partition="train", record_ids=ids)
        with pytest.raises(RuntimeError, match="refit"):
            selector.fit(X, y, partition="train", record_ids=ids)

        payload = selector.to_dict()
        assert payload["fit_partition"] == "train"
        assert payload["fit_record_ids_sha256"] is not None
