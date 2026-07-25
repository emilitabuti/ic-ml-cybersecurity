from pathlib import Path

import numpy as np

import config
from src.training.data_preparation import prepare_windowed_binary_arrays
from src.training.train_lstm import FALLBACK_REASON, train_lstm_or_mlp


def test_train_lstm_uses_explicit_mlp_fallback_when_tensorflow_is_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    rng = np.random.default_rng(config.RANDOM_SEED)
    X = rng.normal(size=(20, 3))
    y = np.array([0, 1] * 10)
    prepared = prepare_windowed_binary_arrays(
        X=X,
        y=y,
        attack_types=np.where(y == 1, "Brute Force", "BENIGN"),
        window_size=5,
    )
    monkeypatch.setattr("src.training.train_lstm.tensorflow_available", lambda: False)
    monkeypatch.setattr(config, "MLP_MAX_ITER", 1)
    monkeypatch.setattr(config, "MLP_HIDDEN_LAYER_SIZES", "2")

    result = train_lstm_or_mlp(
        prepared=prepared,
        use_mlflow=False,
        n_splits=2,
        output_dir=str(tmp_path),
        allow_mlp_fallback=True,
    )

    assert result.model_type == "lstm"
    assert result.fallback_used is True
    assert "MLPClassifier fallback" in result.algorithm
    assert FALLBACK_REASON in result.result_path.read_text(encoding="utf-8")
