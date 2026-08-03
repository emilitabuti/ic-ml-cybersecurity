# 02 — Limpeza

A limpeza do UNSW-NB15 padroniza categorias, cria `Binary_Label`, remove
duplicações exatas e trata ausências que representam inexistência de evento.
Ela preserva timestamps e `source_file`, necessários para o protocolo.

```bash
python -m src.data.pipeline.cleaner \
  --output-path data/processed/unsw_nb15_cleaned_temporal.parquet
```

Nenhum escalonamento ou codificação categórica ocorre antes da divisão.
