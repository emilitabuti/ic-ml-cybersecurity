"""Coleta e consolida os arquivos brutos do UNSW-NB15.

Uso:
    cd ml-pipeline/
    python -m src.data.pipeline.collector
"""
import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

UNSW_RAW_PATH = "data/raw/unsw_nb15"
UNSW_OUTPUT_PATH = "data/processed/unsw_nb15_raw_merged.parquet"


def load_parquet_files(path: str) -> pd.DataFrame:
    """Lê todos os arquivos .parquet de um diretório e os consolida.

    Args:
        path: Caminho do diretório contendo os arquivos .parquet brutos.

    Returns:
        DataFrame consolidado com coluna `source_file` para rastreabilidade.
    """
    dataframes = []

    for file in sorted(os.listdir(path)):
        if file.endswith(".parquet"):
            file_path = os.path.join(path, file)
            logger.info("Lendo arquivo: %s", file)
            df = pd.read_parquet(file_path)
            df["source_file"] = file
            dataframes.append(df)

    if not dataframes:
        raise FileNotFoundError(f"Nenhum arquivo .parquet encontrado em: {path}")

    return pd.concat(dataframes, ignore_index=True)


def collect_unsw_nb15() -> None:
    """Consolida os arquivos brutos do UNSW-NB15."""
    logger.info("Iniciando coleta dos arquivos UNSW-NB15...")
    df_merged = load_parquet_files(UNSW_RAW_PATH)

    logger.info("Total de registros: %d | Colunas: %d", len(df_merged), df_merged.shape[1])

    os.makedirs("data/processed", exist_ok=True)
    df_merged.to_parquet(UNSW_OUTPUT_PATH, index=False)
    logger.info("Dataset consolidado salvo em: %s", UNSW_OUTPUT_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    collect_unsw_nb15()
