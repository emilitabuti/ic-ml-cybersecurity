"""Validação de schema dos datasets carregados.

Valida estruturalmente os DataFrames antes de entrar no pipeline de features,
garantindo que o contrato Caroline ↔ Emili seja respeitado.

Uso:
    from src.data.data_validator import validate_binary_dataset
    validate_binary_dataset(df)  # lança DataValidationError se inválido
"""
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path("src/data/schema/features_schema.json")


class DataValidationError(Exception):
    """Levantada quando o dataset viola o contrato de dados."""


def load_schema() -> dict:
    """Carrega o schema formal de features do arquivo JSON.

    Returns:
        Dicionário com o schema de validação.

    Raises:
        FileNotFoundError: Se features_schema.json não existir.
    """
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Schema não encontrado: {SCHEMA_PATH}\n"
            "O arquivo features_schema.json define o contrato Caroline ↔ Emili."
        )
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def validate_no_missing_values(df: pd.DataFrame) -> None:
    """Valida que não há valores ausentes no dataset."""
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        raise DataValidationError(
            f"Valores ausentes encontrados:\n{missing.to_string()}"
        )
    logger.info("✓ Sem valores ausentes")


def validate_no_infinite_values(df: pd.DataFrame) -> None:
    """Valida que não há valores infinitos no dataset."""
    numeric_df = df.select_dtypes(include=[np.number])
    inf_cols = numeric_df.columns[np.isinf(numeric_df).any()].tolist()
    if inf_cols:
        raise DataValidationError(
            f"Valores infinitos encontrados nas colunas: {inf_cols}"
        )
    logger.info("✓ Sem valores infinitos")


def validate_binary_label(df: pd.DataFrame) -> None:
    """Valida que Binary_Label contém apenas 0 e 1."""
    if "Binary_Label" not in df.columns:
        raise DataValidationError("Coluna 'Binary_Label' não encontrada no dataset.")

    unique_values = set(df["Binary_Label"].unique())
    if not unique_values.issubset({0, 1}):
        raise DataValidationError(
            f"Binary_Label contém valores inesperados: {unique_values - {0, 1}}"
        )
    logger.info("✓ Binary_Label válido — classes: %s", sorted(unique_values))


def validate_required_columns(df: pd.DataFrame, required: list[str]) -> None:
    """Valida que todas as colunas obrigatórias estão presentes.

    Args:
        df: DataFrame a validar.
        required: Lista de colunas obrigatórias.
    """
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise DataValidationError(
            f"Colunas obrigatórias ausentes: {missing_cols}"
        )
    logger.info("✓ Todas as %d colunas obrigatórias presentes", len(required))


def validate_binary_dataset(df: pd.DataFrame) -> None:
    """Executa todas as validações no dataset de classificação binária.

    Args:
        df: DataFrame carregado por data_loader.load_binary_dataset().

    Raises:
        DataValidationError: Se qualquer validação falhar.
    """
    logger.info("Validando dataset binário (%d linhas, %d colunas)...", *df.shape)

    validate_no_missing_values(df)
    validate_no_infinite_values(df)
    validate_binary_label(df)

    # Valida contra schema formal (se disponível)
    if SCHEMA_PATH.exists():
        schema = load_schema()
        required_cols = schema.get("required_columns", [])
        if required_cols:
            validate_required_columns(df, required_cols)

    logger.info("✓ Validação concluída com sucesso")


def validate_attacktype_dataset(df: pd.DataFrame) -> None:
    """Executa validações no dataset de classificação de tipo de ataque.

    Args:
        df: DataFrame carregado por data_loader.load_attacktype_dataset().

    Raises:
        DataValidationError: Se qualquer validação falhar.
    """
    logger.info("Validando dataset tipo de ataque (%d linhas, %d colunas)...", *df.shape)

    validate_no_missing_values(df)
    validate_no_infinite_values(df)

    if "Attack_Type_ID" not in df.columns:
        raise DataValidationError("Coluna 'Attack_Type_ID' não encontrada.")

    n_classes = df["Attack_Type_ID"].nunique()
    logger.info("✓ Attack_Type_ID válido — %d classes encontradas", n_classes)
    logger.info("✓ Validação concluída com sucesso")
