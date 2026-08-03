"""Testes da estrutura canônica do pipeline temporal."""

import importlib
import os
from pathlib import Path

import pytest

# Raiz do ml-pipeline (pasta onde este arquivo está em tests/)
ROOT = Path(__file__).parent.parent


class TestDirectoryStructure:
    """Valida que todas as pastas obrigatórias existem."""

    REQUIRED_DIRS = [
        "data/raw",
        "data/processed",
        "data/schema",
        "models",
        "notebooks",
        "src/data",
        "src/features",
        "src/training",
        "src/models",
        "src/api",
        "src/api/routes",
        "src/api/schemas",
        "src/api/services",
        "tests",
    ]

    @pytest.mark.parametrize("directory", REQUIRED_DIRS)
    def test_directory_exists(self, directory: str) -> None:
        path = ROOT / directory
        assert path.is_dir(), f"Pasta obrigatória ausente: {directory}"


class TestRequiredFiles:
    """Valida que os arquivos-chave do scaffolding estão presentes."""

    REQUIRED_FILES = [
        "config.py",
        "requirements.txt",
        ".env.example",
        "README.md",
        "src/__init__.py",
        "src/data/__init__.py",
        "src/features/__init__.py",
        "src/training/__init__.py",
        "src/models/__init__.py",
        "src/api/__init__.py",
        "src/api/routes/__init__.py",
        "src/api/schemas/__init__.py",
        "src/api/services/__init__.py",
        "src/api/main.py",
        "tests/__init__.py",
    ]

    @pytest.mark.parametrize("filepath", REQUIRED_FILES)
    def test_file_exists(self, filepath: str) -> None:
        path = ROOT / filepath
        assert path.is_file(), f"Arquivo obrigatório ausente: {filepath}"


class TestConfigPy:
    """Valida o conteúdo de config.py."""

    def test_random_seed_is_42(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT))
        import config  # noqa: PLC0415

        importlib.reload(config)
        assert config.RANDOM_SEED == 42, "RANDOM_SEED deve ser 42"

    def test_window_size_is_integer(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT))
        import config  # noqa: PLC0415

        importlib.reload(config)
        assert isinstance(config.WINDOW_SIZE, int), "WINDOW_SIZE deve ser int"

    def test_confidence_threshold_is_float(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT))
        import config  # noqa: PLC0415

        importlib.reload(config)
        assert isinstance(
            config.CONFIDENCE_THRESHOLD, float
        ), "CONFIDENCE_THRESHOLD deve ser float"

    def test_model_artifact_path_is_string(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT))
        import config  # noqa: PLC0415

        importlib.reload(config)
        assert isinstance(
            config.MODEL_ARTIFACT_PATH, str
        ), "MODEL_ARTIFACT_PATH deve ser str"


class TestDotEnvExample:
    """Valida que .env.example documenta as variáveis necessárias."""

    REQUIRED_VARS = ["MODEL_ARTIFACT_PATH", "CONFIDENCE_THRESHOLD"]

    def test_env_example_contains_required_vars(self) -> None:
        env_example = (ROOT / ".env.example").read_text()
        for var in self.REQUIRED_VARS:
            assert var in env_example, f"Variável {var} ausente no .env.example"


class TestRequirementsTxt:
    """Valida que requirements.txt tem as dependências essenciais."""

    REQUIRED_PACKAGES = [
        "fastapi",
        "uvicorn",
        "scikit-learn",
        "pandas",
        "numpy",
        "pydantic",
        "joblib",
        "python-dotenv",
        "tensorflow",
    ]

    def test_requirements_has_essential_packages(self) -> None:
        reqs = (ROOT / "requirements.txt").read_text().lower()
        for pkg in self.REQUIRED_PACKAGES:
            assert pkg.lower() in reqs, f"Pacote {pkg} ausente no requirements.txt"


class TestFastAPIApp:
    """Valida que a aplicação FastAPI inicia e responde corretamente."""

    def test_app_is_importable(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT))
        from src.api.main import app  # noqa: PLC0415

        assert app is not None

    def test_health_endpoint_returns_ok(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT))
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from src.api.main import app  # noqa: PLC0415

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
