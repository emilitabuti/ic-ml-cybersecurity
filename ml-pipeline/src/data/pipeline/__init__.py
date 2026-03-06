"""Pipeline de pré-processamento de dados — adaptado do trabalho de Caroline.

Módulos:
    collector   — consolida arquivos parquet brutos em um único dataset
    cleaner     — limpeza, deduplicação e normalização de labels
    scaler      — escalonamento com log1p + RobustScaler
    preprocessor — geração dos datasets model-ready (binário e multi-classe)
"""
