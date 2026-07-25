from pathlib import Path
from types import SimpleNamespace

import src.training.mlflow_utils as mlflow_utils
from src.training.mlflow_utils import experiment_name, setup_mlflow_tracking


def test_experiment_name_uses_project_prefix() -> None:
    assert experiment_name("random_forest") == "ic-ml-cybersecurity-random_forest"


def test_setup_mlflow_tracking_creates_local_mlruns_and_enables_sklearn_autolog(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: dict[str, object] = {}
    fake_mlflow = SimpleNamespace(
        set_tracking_uri=lambda uri: calls.setdefault("uri", uri),
        set_experiment=lambda name: calls.setdefault("experiment", name),
        sklearn=SimpleNamespace(autolog=lambda: calls.setdefault("sklearn_autolog", True)),
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mlflow_utils, "mlflow", fake_mlflow)

    name = setup_mlflow_tracking("decision_tree", flavor="sklearn")

    assert name == "ic-ml-cybersecurity-decision_tree"
    assert (tmp_path / "mlruns").is_dir()
    assert calls["uri"] == str(tmp_path / "mlruns")
    assert calls["experiment"] == "ic-ml-cybersecurity-decision_tree"
    assert calls["sklearn_autolog"] is True


def test_setup_mlflow_tracking_enables_tensorflow_autolog(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}
    fake_mlflow = SimpleNamespace(
        set_tracking_uri=lambda uri: calls.setdefault("uri", uri),
        set_experiment=lambda name: calls.setdefault("experiment", name),
        tensorflow=SimpleNamespace(
            autolog=lambda: calls.setdefault("tensorflow_autolog", True)
        ),
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mlflow_utils, "mlflow", fake_mlflow)

    setup_mlflow_tracking("lstm", flavor="tensorflow")

    assert calls["experiment"] == "ic-ml-cybersecurity-lstm"
    assert calls["tensorflow_autolog"] is True
