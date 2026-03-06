"""
Testes de ingestão e validação do dataset CICIDS2017 — Story 1.3.

Valida que:
- data_loader carrega corretamente arquivos parquet model-ready
- Erros claros são gerados quando arquivo não existe ou colunas estão ausentes
- data_validator detecta e reporta NaN, infinitos e Binary_Label inválido
- Erros de validação são descritivos (não silenciados)
"""
import pathlib

import numpy as np
import pandas as pd
import pytest

from src.data.data_validator import (
    DataValidationError,
    validate_binary_dataset,
    validate_attacktype_dataset,
    validate_binary_label,
    validate_no_missing_values,
    validate_no_infinite_values,
)


# ── Fixtures — DataFrames sintéticos que imitam a estrutura CIC-IDS2017 ───────


@pytest.fixture
def valid_binary_df() -> pd.DataFrame:
    """DataFrame válido de classificação binária — estrutura CIC-IDS2017."""
    rng = np.random.default_rng(42)
    n = 200
    return pd.DataFrame({
        "Flow_Duration": rng.uniform(0, 1, n),
        "Total_Fwd_Packets": rng.uniform(0, 1, n),
        "Total_Backward_Packets": rng.uniform(0, 1, n),
        "Flow_Bytes_s": rng.uniform(0, 1, n),
        "Flow_Packets_s": rng.uniform(0, 1, n),
        "Binary_Label": rng.integers(0, 2, n),
    })


@pytest.fixture
def valid_attacktype_df(valid_binary_df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame válido de classificação de tipo de ataque (somente ataques)."""
    df = valid_binary_df[valid_binary_df["Binary_Label"] == 1].copy()
    # Garante ao menos algumas amostras de ataque
    if len(df) == 0:
        df = valid_binary_df.copy()
        df["Binary_Label"] = 1
    df["Attack_Type"] = "DDoS"
    df["Attack_Type_ID"] = 0
    return df


@pytest.fixture
def binary_parquet(tmp_path: "pathlib.Path", valid_binary_df: pd.DataFrame) -> str:
    """Parquet temporário com dataset binário válido."""
    path = tmp_path / "cic_ids2017_model_ready_binary.parquet"
    valid_binary_df.to_parquet(path, index=False)
    return str(path)


@pytest.fixture
def attacktype_parquet(
    tmp_path: "pathlib.Path", valid_attacktype_df: pd.DataFrame
) -> str:
    """Parquet temporário com dataset de tipo de ataque válido."""
    path = tmp_path / "cic_ids2017_model_ready_attacktype.parquet"
    valid_attacktype_df.to_parquet(path, index=False)
    return str(path)


# ── TestDataValidator — validações estruturais ────────────────────────────────


class TestValidateNoMissingValues:
    """Valida detecção e reporte de valores ausentes."""

    def test_passes_with_no_missing(self, valid_binary_df: pd.DataFrame) -> None:
        """Não deve lançar exceção quando não há NaN."""
        validate_no_missing_values(valid_binary_df)

    def test_raises_with_missing_values(self, valid_binary_df: pd.DataFrame) -> None:
        """Deve lançar DataValidationError com mensagem descritiva."""
        df_with_nan = valid_binary_df.copy()
        df_with_nan.loc[0, "Flow_Duration"] = float("nan")

        with pytest.raises(DataValidationError, match="Valores ausentes encontrados"):
            validate_no_missing_values(df_with_nan)

    def test_error_message_includes_column_name(self, valid_binary_df: pd.DataFrame) -> None:
        """A mensagem de erro deve identificar qual coluna tem NaN."""
        df_with_nan = valid_binary_df.copy()
        df_with_nan.loc[0:5, "Total_Fwd_Packets"] = float("nan")

        with pytest.raises(DataValidationError, match="Total_Fwd_Packets"):
            validate_no_missing_values(df_with_nan)


class TestValidateNoInfiniteValues:
    """Valida detecção de valores infinitos."""

    def test_passes_with_no_infinite(self, valid_binary_df: pd.DataFrame) -> None:
        """Não deve lançar exceção quando não há infinitos."""
        validate_no_infinite_values(valid_binary_df)

    def test_raises_with_positive_infinite(self, valid_binary_df: pd.DataFrame) -> None:
        """Deve detectar +inf."""
        df_with_inf = valid_binary_df.copy()
        df_with_inf.loc[0, "Flow_Bytes_s"] = float("inf")

        with pytest.raises(DataValidationError, match="infinitos"):
            validate_no_infinite_values(df_with_inf)

    def test_raises_with_negative_infinite(self, valid_binary_df: pd.DataFrame) -> None:
        """Deve detectar -inf."""
        df_with_inf = valid_binary_df.copy()
        df_with_inf.loc[0, "Flow_Packets_s"] = float("-inf")

        with pytest.raises(DataValidationError, match="infinitos"):
            validate_no_infinite_values(df_with_inf)


class TestValidateBinaryLabel:
    """Valida a integridade da coluna Binary_Label."""

    def test_passes_with_valid_binary_label(self, valid_binary_df: pd.DataFrame) -> None:
        """Deve aceitar DataFrame com Binary_Label = 0 e 1."""
        validate_binary_label(valid_binary_df)

    def test_raises_when_column_missing(self, valid_binary_df: pd.DataFrame) -> None:
        """Deve falhar claramente quando Binary_Label não existe."""
        df_no_label = valid_binary_df.drop(columns=["Binary_Label"])

        with pytest.raises(DataValidationError, match="Binary_Label"):
            validate_binary_label(df_no_label)

    def test_raises_with_invalid_label_value(self, valid_binary_df: pd.DataFrame) -> None:
        """Deve rejeitar valores além de 0 e 1 (ex: 2, -1)."""
        df_invalid = valid_binary_df.copy()
        df_invalid.loc[0, "Binary_Label"] = 99

        with pytest.raises(DataValidationError, match="valores inesperados"):
            validate_binary_label(df_invalid)


class TestValidateBinaryDataset:
    """Validação completa do dataset binário."""

    def test_passes_for_valid_dataset(self, valid_binary_df: pd.DataFrame) -> None:
        """Dataset válido deve passar em todas as validações."""
        validate_binary_dataset(valid_binary_df)

    def test_raises_for_nan_in_feature(self, valid_binary_df: pd.DataFrame) -> None:
        """Valores ausentes em qualquer feature devem ser detectados."""
        df_bad = valid_binary_df.copy()
        df_bad.loc[10, "Flow_Duration"] = float("nan")

        with pytest.raises(DataValidationError):
            validate_binary_dataset(df_bad)

    def test_raises_for_missing_binary_label(self, valid_binary_df: pd.DataFrame) -> None:
        """Ausência de Binary_Label deve gerar erro descritivo."""
        df_no_label = valid_binary_df.drop(columns=["Binary_Label"])

        with pytest.raises(DataValidationError, match="Binary_Label"):
            validate_binary_dataset(df_no_label)


class TestValidateAttacktypeDataset:
    """Validação do dataset de tipo de ataque."""

    def test_passes_for_valid_dataset(self, valid_attacktype_df: pd.DataFrame) -> None:
        """Dataset válido de tipo de ataque deve passar."""
        validate_attacktype_dataset(valid_attacktype_df)

    def test_raises_when_attack_type_id_missing(
        self, valid_attacktype_df: pd.DataFrame
    ) -> None:
        """Ausência de Attack_Type_ID deve gerar erro."""
        df_no_id = valid_attacktype_df.drop(columns=["Attack_Type_ID"])

        with pytest.raises(DataValidationError, match="Attack_Type_ID"):
            validate_attacktype_dataset(df_no_id)


# ── TestDataLoader — carregamento de arquivos ─────────────────────────────────


class TestDataLoaderFileNotFound:
    """Valida erros claros quando arquivo não existe."""

    def test_raises_file_not_found_with_helpful_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """FileNotFoundError deve incluir instruções do pipeline de pré-processamento."""
        import src.data.data_loader as loader
        from pathlib import Path

        monkeypatch.setitem(
            loader._PATHS["cic"], "binary",
            Path("data/processed/arquivo_que_nao_existe.parquet")
        )

        with pytest.raises(FileNotFoundError, match="pipeline de pré-processamento"):
            loader.load_dataset(dataset="cic", task="binary")

    def test_raises_value_error_for_invalid_dataset(self) -> None:
        """Dataset inválido deve gerar ValueError."""
        from src.data.data_loader import load_dataset

        with pytest.raises(ValueError, match="Dataset inválido"):
            load_dataset(dataset="inexistente", task="binary")  # type: ignore[arg-type]

    def test_raises_value_error_for_invalid_task(self) -> None:
        """Task inválida deve gerar ValueError."""
        from src.data.data_loader import load_dataset

        with pytest.raises(ValueError, match="Task inválida"):
            load_dataset(dataset="cic", task="invalida")  # type: ignore[arg-type]


class TestLoadBinaryDataset:
    """Valida carregamento do dataset binário com dados sintéticos."""

    def test_returns_numpy_arrays(
        self, binary_parquet: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_binary_dataset deve retornar (X, y) como arrays numpy."""
        import src.data.data_loader as loader
        from pathlib import Path

        monkeypatch.setitem(loader._PATHS["cic"], "binary", Path(binary_parquet))

        X, y = loader.load_binary_dataset(dataset="cic")

        assert isinstance(X, np.ndarray)
        assert isinstance(y, np.ndarray)

    def test_y_contains_only_binary_values(
        self, binary_parquet: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """y deve conter apenas 0 e 1."""
        import src.data.data_loader as loader
        from pathlib import Path

        monkeypatch.setitem(loader._PATHS["cic"], "binary", Path(binary_parquet))

        _, y = loader.load_binary_dataset(dataset="cic")

        assert set(np.unique(y)).issubset({0, 1})

    def test_x_does_not_contain_label_columns(
        self, binary_parquet: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """X não deve incluir colunas alvo (Binary_Label, Attack_Type_ID, etc.)."""
        import src.data.data_loader as loader
        from pathlib import Path

        monkeypatch.setitem(loader._PATHS["cic"], "binary", Path(binary_parquet))

        feature_names = loader.get_feature_names(dataset="cic", task="binary")

        for non_feature in ["Binary_Label", "Attack_Type", "Attack_Type_ID"]:
            assert non_feature not in feature_names

    def test_x_shape_consistent_with_dataset(
        self, binary_parquet: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """X.shape[0] deve ser igual ao número de linhas do dataset."""
        import src.data.data_loader as loader
        from pathlib import Path

        monkeypatch.setitem(loader._PATHS["cic"], "binary", Path(binary_parquet))

        df = loader.load_dataset(dataset="cic", task="binary")
        X, y = loader.load_binary_dataset(dataset="cic")

        assert X.shape[0] == len(df)
        assert y.shape[0] == len(df)
