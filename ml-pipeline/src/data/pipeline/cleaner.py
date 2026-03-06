"""Limpeza e tratamento dos datasets consolidados.

Aplica deduplicação, padronização de nomes, correção de encoding de labels,
tratamento de valores ausentes e infinitos.

Uso:
    cd ml-pipeline/
    python -m src.data.pipeline.cleaner --dataset cic
    python -m src.data.pipeline.cleaner --dataset unsw
"""
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── CIC-IDS2017 ──────────────────────────────────────────────────────────────

CIC_INPUT_PATH = "data/processed/cic_ids2017_raw_merged.parquet"
CIC_OUTPUT_PATH = "data/processed/cic_ids2017_cleaned.parquet"

# ── UNSW-NB15 ─────────────────────────────────────────────────────────────────

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
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    nan_count = df.isnull().sum().sum()
    if nan_count > 0:
        logger.info("Preenchendo %d valores NaN/inf com 0", nan_count)
    df.fillna(0, inplace=True)
    return df


def clean_cic_ids2017() -> None:
    """Limpa o dataset CIC-IDS2017 consolidado."""
    logger.info("Carregando CIC-IDS2017 consolidado: %s", CIC_INPUT_PATH)
    df = pd.read_parquet(CIC_INPUT_PATH)

    df = remove_duplicate_columns(df)
    df = clean_column_names(df)

    # Corrige caracteres corrompidos no campo Label
    df["Label"] = df["Label"].str.replace("\\ufffd", "", regex=False).str.strip()

    # Cria coluna binária
    df["Binary_Label"] = df["Label"].apply(lambda x: 0 if x == "BENIGN" else 1)
    logger.info("Binary_Label criado — Benignos: %d | Ataques: %d",
                (df["Binary_Label"] == 0).sum(), (df["Binary_Label"] == 1).sum())

    df = remove_duplicate_rows(df)
    df = treat_infinite_and_missing(df)

    logger.info("CIC-IDS2017 limpo — linhas: %d | colunas: %d", df.shape[0], df.shape[1])
    df.to_parquet(CIC_OUTPUT_PATH, index=False)
    logger.info("Dataset limpo salvo em: %s", CIC_OUTPUT_PATH)


def clean_unsw_nb15() -> None:
    """Limpa o dataset UNSW-NB15 consolidado."""
    logger.info("Carregando UNSW-NB15 consolidado: %s", UNSW_INPUT_PATH)
    df = pd.read_parquet(UNSW_INPUT_PATH)

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
    df.to_parquet(UNSW_OUTPUT_PATH, index=False)
    logger.info("Dataset limpo salvo em: %s", UNSW_OUTPUT_PATH)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    parser = argparse.ArgumentParser(description="Limpeza e tratamento dos datasets.")
    parser.add_argument("--dataset", choices=["cic", "unsw", "all"], default="all")
    args = parser.parse_args()

    if args.dataset in ("cic", "all"):
        clean_cic_ids2017()
    if args.dataset in ("unsw", "all"):
        clean_unsw_nb15()
