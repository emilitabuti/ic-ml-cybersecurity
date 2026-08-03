"""Limpeza e tratamento do UNSW-NB15 consolidado.

Aplica deduplicação, padronização de nomes, correção de encoding de labels,
tratamento de valores ausentes e infinitos.

Uso:
    cd ml-pipeline/
    python -m src.data.pipeline.cleaner
"""
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

UNSW_INPUT_PATH = "data/processed/unsw_nb15_raw_merged.parquet"
UNSW_OUTPUT_PATH = "data/processed/unsw_nb15_cleaned.parquet"

# Mapeamento de categorias inconsistentes no UNSW-NB15
UNSW_CATEGORY_MAPPING = {
    "Fuzzers": "Fuzzer",
    "Backdoors": "Backdoor",
}


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza nomes de colunas para snake_case."""
    df.columns = (
        df.columns
        .str.strip()
        .str.replace(" ", "_", regex=False)
        .str.replace("/", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df


def remove_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove colunas com sufixo 'duplicated' geradas pela consolidação."""
    duplicate_cols = [col for col in df.columns if "duplicated" in col]
    if duplicate_cols:
        logger.info("Removendo %d colunas duplicadas: %s", len(duplicate_cols), duplicate_cols)
    return df.drop(columns=duplicate_cols)


def remove_duplicate_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove linhas duplicadas preservando a primeira ocorrência."""
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    logger.info("Linhas removidas por duplicação: %d", removed)
    return df


def treat_infinite_and_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Substitui inf/-inf por NaN e preenche NaN com 0."""
    df = df.replace([np.inf, -np.inf], np.nan)
    nan_count = df.isnull().sum().sum()
    if nan_count > 0:
        logger.info("Preenchendo %d valores NaN/inf com 0", nan_count)
    df = df.fillna(0)
    return df


def clean_unsw_nb15(
    input_path: str | Path = UNSW_INPUT_PATH,
    output_path: str | Path = UNSW_OUTPUT_PATH,
    *,
    overwrite: bool = True,
) -> Path:
    """Limpa o dataset UNSW-NB15 consolidado."""
    source, destination = _resolve_io_paths(input_path, output_path, overwrite=overwrite)
    logger.info("Carregando UNSW-NB15 consolidado: %s", source)
    df = pd.read_parquet(source)

    # Padroniza attack_cat
    df["attack_cat"] = df["attack_cat"].astype(str).str.strip()
    df["attack_cat"] = df["attack_cat"].replace(UNSW_CATEGORY_MAPPING)
    df["attack_cat"] = df["attack_cat"].replace("None", "BENIGN")

    # Cria coluna binária a partir do campo label existente
    df["Binary_Label"] = df["label"].astype(int)

    df = remove_duplicate_rows(df)

    # Trata colunas com muitos NaN (ausência de evento, não dado inválido)
    for col in ["is_ftp_login", "ct_flw_http_mthd"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    logger.info("UNSW-NB15 limpo — linhas: %d | colunas: %d", df.shape[0], df.shape[1])
    df.to_parquet(destination, index=False)
    logger.info("Dataset limpo salvo em: %s", destination)
    return destination


def _resolve_io_paths(
    input_path: str | Path,
    output_path: str | Path,
    *,
    overwrite: bool,
) -> tuple[Path, Path]:
    """Valida entrada e saída antes de materializar um dataset limpo."""
    source = Path(input_path)
    destination = Path(output_path)
    if not source.exists():
        raise FileNotFoundError(f"Dataset de entrada não encontrado: {source}")
    if source.resolve() == destination.resolve():
        raise ValueError("O caminho de saída deve ser diferente do arquivo de entrada.")
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"O arquivo de saída já existe: {destination}. "
            "Use overwrite=True somente após validar o destino."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    return source, destination


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    import argparse
    parser = argparse.ArgumentParser(description="Limpeza do UNSW-NB15.")
    parser.add_argument("--input-path", default=None)
    parser.add_argument("--output-path", default=None)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permite substituir explicitamente um arquivo de saída existente.",
    )
    args = parser.parse_args()

    clean_unsw_nb15(
        input_path=args.input_path or UNSW_INPUT_PATH,
        output_path=args.output_path or UNSW_OUTPUT_PATH,
        overwrite=args.overwrite,
    )
