"""Seleção de features por importância de Random Forest.

O seletor deve ser ajustado exclusivamente com dados de treino. A lista
persistida de features selecionadas é então reutilizada para transformar
treino, teste e futuros dados de inferência sem recalcular importâncias.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from hashlib import sha256
import tempfile
from typing import Any, Optional

import numpy as np
from sklearn.ensemble import RandomForestClassifier

import config

logger = logging.getLogger(__name__)


class RandomForestFeatureSelector:
    """Seleciona features usando importâncias calculadas por Random Forest."""

    def __init__(
        self,
        feature_names: list[str],
        top_n: Optional[int] = None,
        threshold: Optional[float] = None,
        artifact_path: str | Path | None = None,
        random_state: Optional[int] = None,
        n_estimators: int = 100,
        n_jobs: int = 1,
    ) -> None:
        self.feature_names = list(feature_names)
        self.top_n = config.FEATURE_SELECTION_TOP_N if top_n is None and threshold is None else top_n
        self.threshold = (
            config.FEATURE_SELECTION_THRESHOLD if threshold is None else threshold
        )
        self.artifact_path = Path(
            artifact_path
            if artifact_path is not None
            else config.FEATURE_SELECTION_ARTIFACT_PATH
        )
        self.random_state = (
            config.RANDOM_SEED if random_state is None else random_state
        )
        self.n_estimators = n_estimators
        self.n_jobs = n_jobs

        self._validate_init_params()

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        *,
        partition: str | None = None,
        record_ids: np.ndarray | None = None,
    ) -> "RandomForestFeatureSelector":
        """Calcula importâncias e define features selecionadas com dados de treino."""
        if hasattr(self, "feature_importances_"):
            raise RuntimeError("O seletor já foi ajustado; refit é proibido.")
        X_array = np.asarray(X)
        y_array = np.asarray(y)
        self._validate_fit_input(X_array, y_array)
        self._validate_fit_audit(
            partition=partition,
            record_ids=record_ids,
            n_samples=X_array.shape[0],
        )

        logger.info(
            "Calculando feature selection com RandomForest: samples=%d | features=%d | seed=%d",
            X_array.shape[0],
            X_array.shape[1],
            self.random_state,
        )
        model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
        )
        model.fit(X_array, y_array)

        self.feature_importances_ = model.feature_importances_.astype(float)
        self.n_training_samples_ = int(X_array.shape[0])
        self.n_input_features_ = int(X_array.shape[1])
        self.selected_indices_ = self._select_indices(self.feature_importances_)
        self.selected_feature_names_ = [
            self.feature_names[index] for index in self.selected_indices_
        ]
        self.fit_partition_ = partition or "unspecified_legacy"
        self.fit_record_ids_sha256_ = (
            _record_ids_sha256(record_ids) if record_ids is not None else None
        )

        logger.info(
            "Feature selection concluida: selected=%d | total=%d",
            len(self.selected_indices_),
            self.n_input_features_,
        )
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Aplica a seleção já calculada sem refit."""
        self._ensure_fitted()
        X_array = np.asarray(X)
        if X_array.ndim != 2:
            raise ValueError("X deve ser 2D, com shape (n_samples, n_features).")
        if X_array.shape[1] != self.n_input_features_:
            raise ValueError(
                "X tem quantidade de features incompatível com a seleção: "
                f"esperado {self.n_input_features_}, recebido {X_array.shape[1]}."
            )
        return X_array[:, self.selected_indices_]

    def fit_transform(
        self,
        X: np.ndarray,
        y: np.ndarray,
        *,
        partition: str | None = None,
        record_ids: np.ndarray | None = None,
    ) -> np.ndarray:
        """Executa `fit()` no treino e retorna `transform()` do mesmo conjunto."""
        return self.fit(
            X,
            y,
            partition=partition,
            record_ids=record_ids,
        ).transform(X)

    def save(self, artifact_path: str | Path | None = None) -> Path:
        """Persiste a seleção em JSON para reuso consistente."""
        self._ensure_fitted()
        path = Path(artifact_path) if artifact_path is not None else self.artifact_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        try:
            json.loads(temporary.read_text(encoding="utf-8"))
            temporary.replace(path)
        finally:
            if temporary.exists():
                temporary.unlink()
        logger.info("Feature selection persistida em %s", path)
        return path

    @classmethod
    def load(cls, artifact_path: str | Path) -> "RandomForestFeatureSelector":
        """Carrega uma seleção persistida sem treinar Random Forest."""
        path = Path(artifact_path)
        payload = json.loads(path.read_text(encoding="utf-8"))

        selector = cls(
            feature_names=list(payload["feature_names"]),
            top_n=payload["top_n"],
            threshold=payload["threshold"],
            artifact_path=path,
            random_state=payload["random_state"],
            n_estimators=payload.get("n_estimators", 100),
            n_jobs=payload.get("n_jobs", 1),
        )
        selector.feature_importances_ = np.asarray(
            payload["feature_importances"],
            dtype=float,
        )
        selector.selected_indices_ = np.asarray(payload["selected_indices"], dtype=int)
        selector.selected_feature_names_ = list(payload["selected_feature_names"])
        selector.n_training_samples_ = int(payload["n_training_samples"])
        selector.n_input_features_ = int(payload["n_input_features"])
        selector.fit_partition_ = payload.get("fit_partition", "unspecified_legacy")
        selector.fit_record_ids_sha256_ = payload.get("fit_record_ids_sha256")
        return selector

    def to_dict(self) -> dict[str, Any]:
        """Retorna payload serializável do artefato de seleção."""
        self._ensure_fitted()
        return {
            "feature_names": self.feature_names,
            "selected_feature_names": self.selected_feature_names_,
            "selected_indices": self.selected_indices_.astype(int).tolist(),
            "feature_importances": self.feature_importances_.astype(float).tolist(),
            "top_n": self.top_n,
            "threshold": self.threshold,
            "random_state": self.random_state,
            "n_estimators": self.n_estimators,
            "n_jobs": self.n_jobs,
            "n_training_samples": self.n_training_samples_,
            "n_input_features": self.n_input_features_,
            "fit_partition": self.fit_partition_,
            "fit_record_ids_sha256": self.fit_record_ids_sha256_,
        }

    def _select_indices(self, importances: np.ndarray) -> np.ndarray:
        indices = np.arange(importances.shape[0])
        sorted_indices = np.lexsort((indices, -importances))

        if self.threshold is not None and self.threshold > 0:
            selected = sorted_indices[importances[sorted_indices] >= self.threshold]
        else:
            limit = min(int(self.top_n), importances.shape[0])
            selected = sorted_indices[:limit]

        if selected.size == 0:
            raise ValueError(
                "Nenhuma feature selecionada. Reduza FEATURE_SELECTION_THRESHOLD "
                "ou configure FEATURE_SELECTION_TOP_N."
            )
        return selected.astype(int)

    def _validate_init_params(self) -> None:
        if not self.feature_names:
            raise ValueError("feature_names deve conter ao menos uma feature.")
        if self.top_n is None and (self.threshold is None or self.threshold <= 0):
            raise ValueError("Configure top_n positivo ou threshold maior que zero.")
        if self.top_n is not None and self.top_n < 1:
            raise ValueError("top_n deve ser maior ou igual a 1.")
        if self.threshold is not None and self.threshold < 0:
            raise ValueError("threshold deve ser maior ou igual a 0.")
        if self.n_estimators < 1:
            raise ValueError("n_estimators deve ser maior ou igual a 1.")
        if self.n_jobs == 0:
            raise ValueError("n_jobs não pode ser zero.")

    def _validate_fit_input(self, X: np.ndarray, y: np.ndarray) -> None:
        if X.ndim != 2:
            raise ValueError("X deve ser 2D, com shape (n_samples, n_features).")
        if y.ndim != 1:
            raise ValueError("y deve ser 1D, com shape (n_samples,).")
        if X.shape[0] != y.shape[0]:
            raise ValueError("X e y devem ter o mesmo número de amostras.")
        if X.shape[1] != len(self.feature_names):
            raise ValueError(
                "feature_names deve ter o mesmo tamanho do eixo de features de X: "
                f"esperado {X.shape[1]}, recebido {len(self.feature_names)}."
            )

    def _ensure_fitted(self) -> None:
        required_attrs = (
            "feature_importances_",
            "selected_indices_",
            "selected_feature_names_",
            "n_training_samples_",
            "n_input_features_",
        )
        if not all(hasattr(self, attr) for attr in required_attrs):
            raise ValueError("Feature selector ainda nao foi ajustado ou carregado.")

    @staticmethod
    def _validate_fit_audit(
        *,
        partition: str | None,
        record_ids: np.ndarray | None,
        n_samples: int,
    ) -> None:
        if partition is not None and partition != "train":
            raise ValueError(
                "O seletor temporal só pode ser ajustado com partition='train'."
            )
        if record_ids is None:
            return
        ids = np.asarray(record_ids)
        if ids.ndim != 1 or len(ids) != n_samples:
            raise ValueError("record_ids deve ser 1D e acompanhar todas as amostras.")
        if len(np.unique(ids)) != len(ids):
            raise ValueError("record_ids deve ser único no ajuste do seletor.")


def _record_ids_sha256(record_ids: np.ndarray) -> str:
    return sha256(np.asarray(record_ids, dtype="<i8").tobytes()).hexdigest()
