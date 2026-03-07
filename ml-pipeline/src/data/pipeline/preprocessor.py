"""Geração dos datasets prontos para modelagem (model-ready).

Produz dois conjuntos finais para cada dataset:
  - *_model_ready_binary.parquet   — classificação binária (Benigno vs Ataque)
  - *_model_ready_attacktype.parquet — classificação do tipo de ataque (somente ataques)

Uso:
    cd ml-pipeline/
    python -m src.data.pipeline.preprocessor --dataset cic
    python -m src.data.pipeline.preprocessor --dataset unsw
"""
import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)


def make_model_ready(
    input_path: str,
    output_binary_path: str,
    output_attacktype_path: str,
    dataset_name: str,
) -> None:
    """Transforma dataset escalado nos datasets finais para modelagem.

    Gera dois arquivos:
    - Binário: todas as amostras, target = Binary_Label (0=benigno, 1=ataque)
    - Tipo de ataque: apenas ataques, target = Attack_Type_ID (multi-classe)

    Args:
        input_path: Parquet escalado de entrada.
        output_binary_path: Caminho de saída do dataset binário.
        output_attacktype_path: Caminho de saída do dataset de tipo de ataque.
        dataset_name: Nome do dataset para logging.
    """
    logger.info("Processando %s: %s", dataset_name, input_path)
    df = pd.read_parquet(input_path)

    # Determina coluna de tipo de ataque conforme o dataset
    if "attack_cat" in df.columns:
        df["Attack_Type"] = df["attack_cat"].astype(str)
    elif "Label" in df.columns:
        df["Attack_Type"] = df["Label"].astype(str)
    else:
        df["Attack_Type"] = "UNKNOWN"
        logger.warning("Coluna de tipo de ataque não encontrada — usando 'UNKNOWN'")

    # Garante Binary_Label
    if "Binary_Label" not in df.columns:
        if "label" in df.columns:
            df["Binary_Label"] = df["label"].astype(int)
        else:
            raise ValueError("Binary_Label não encontrado e não foi possível inferir.")

    # Colunas categóricas de features (apenas UNSW-NB15 possui)
    feature_cat_cols = [c for c in ["proto", "state", "service"] if c in df.columns]

    # Remove colunas de label original (não entram como features)
    drop_as_features = [c for c in ["Label", "attack_cat", "source_file"] if c in df.columns]
    df_binary = df.drop(columns=drop_as_features, errors="ignore")

    # One-hot encoding nas features categóricas
    if feature_cat_cols:
        df_binary = pd.get_dummies(df_binary, columns=feature_cat_cols, drop_first=False)
        logger.info("One-hot encoding aplicado em: %s", feature_cat_cols)

    logger.info("Dataset binário — linhas: %d | colunas: %d", len(df_binary), df_binary.shape[1])

    # Dataset de tipo de ataque: apenas amostras maliciosas
    df_attack = df_binary[df_binary["Binary_Label"] == 1].copy()

    classes = sorted(df_attack["Attack_Type"].unique().tolist())
    class_to_id = {c: i for i, c in enumerate(classes)}
    df_attack["Attack_Type_ID"] = df_attack["Attack_Type"].map(class_to_id).astype(int)

    logger.info("Dataset tipo de ataque — classes: %d | linhas: %d", len(classes), len(df_attack))

    os.makedirs("data/processed", exist_ok=True)
    df_binary.to_parquet(output_binary_path, index=False)
    df_attack.to_parquet(output_attacktype_path, index=False)

    logger.info("Salvo (binário): %s", output_binary_path)
    logger.info("Salvo (tipo de ataque): %s", output_attacktype_path)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    parser = argparse.ArgumentParser(description="Gera datasets model-ready.")
    parser.add_argument("--dataset", choices=["cic", "unsw", "all"], default="all")
    args = parser.parse_args()

    if args.dataset in ("cic", "all"):
        make_model_ready(
            input_path="data/processed/cic_ids2017_scaled.parquet",
            output_binary_path="data/processed/cic_ids2017_model_ready_binary.parquet",
            output_attacktype_path="data/processed/cic_ids2017_model_ready_attacktype.parquet",
            dataset_name="CIC-IDS2017",
        )
    if args.dataset in ("unsw", "all"):
        make_model_ready(
            input_path="data/processed/unsw_nb15_scaled.parquet",
            output_binary_path="data/processed/unsw_nb15_model_ready_binary.parquet",
            output_attacktype_path="data/processed/unsw_nb15_model_ready_attacktype.parquet",
            dataset_name="UNSW-NB15",
        )
