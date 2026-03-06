"""Escalonamento dos datasets limpos.

Aplica transformação log1p em colunas altamente assimétricas seguida de
RobustScaler, preservando outliers relevantes para detecção de ataques.

Uso:
    cd ml-pipeline/
    python -m src.data.pipeline.scaler --dataset cic
    python -m src.data.pipeline.scaler --dataset unsw
"""
import logging

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

logger = logging.getLogger(__name__)

# Colunas que nunca devem ser escalonadas
_EXCLUDE_FROM_SCALING = {"Binary_Label", "Label", "attack_cat", "source_file"}

# Limiares para log1p: aplica apenas em colunas não-negativas com max muito alto
_LOG1P_MAX_THRESHOLD = 1e6


def scale_dataset(input_path: str, output_path: str) -> None:
    """Escala um dataset limpo usando log1p + RobustScaler.

    Args:
        input_path: Caminho do parquet limpo (ex: *_cleaned.parquet).
        output_path: Caminho de saída (ex: *_scaled.parquet).
    """
    logger.info("Carregando dataset: %s", input_path)
    df = pd.read_parquet(input_path)
    df_scaled = df.copy()

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in _EXCLUDE_FROM_SCALING]
    logger.info("Colunas numéricas a escalar: %d", len(numeric_cols))

    # 1) log1p em colunas muito assimétricas (não-negativas, max > 1e6)
    log_cols = [
        col for col in numeric_cols
        if df_scaled[col].min() >= 0 and df_scaled[col].max() > _LOG1P_MAX_THRESHOLD
    ]
    if log_cols:
        df_scaled[log_cols] = np.log1p(df_scaled[log_cols])
        logger.info("log1p aplicado em %d colunas", len(log_cols))

    # 2) Sanitiza inf/NaN introduzidos pela transformação
    df_scaled[numeric_cols] = (
        df_scaled[numeric_cols]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    # 3) RobustScaler (usa mediana + IQR — robusto a outliers)
    scaler = RobustScaler()
    df_scaled[numeric_cols] = scaler.fit_transform(df_scaled[numeric_cols])
    logger.info("RobustScaler aplicado")

    df_scaled.to_parquet(output_path, index=False)
    logger.info("Dataset escalado salvo em: %s", output_path)


if __name__ == "__main__":
    import argparse
    import os

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    parser = argparse.ArgumentParser(description="Escalona datasets limpos.")
    parser.add_argument("--dataset", choices=["cic", "unsw", "all"], default="all")
    args = parser.parse_args()

    os.makedirs("data/processed", exist_ok=True)

    if args.dataset in ("cic", "all"):
        scale_dataset(
            "data/processed/cic_ids2017_cleaned.parquet",
            "data/processed/cic_ids2017_scaled.parquet",
        )
    if args.dataset in ("unsw", "all"):
        scale_dataset(
            "data/processed/unsw_nb15_cleaned.parquet",
            "data/processed/unsw_nb15_scaled.parquet",
        )
