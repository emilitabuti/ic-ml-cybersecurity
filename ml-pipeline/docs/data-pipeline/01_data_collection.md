# 01 — Coleta

Os Parquets brutos do UNSW-NB15 devem ser colocados em
`data/raw/unsw_nb15/`. O coletor lê os arquivos em ordem estável, acrescenta
`source_file` e materializa o consolidado sem alterar os arquivos de origem.

```bash
python -m src.data.pipeline.collector
```

Saída: `data/processed/unsw_nb15_raw_merged.parquet`.
