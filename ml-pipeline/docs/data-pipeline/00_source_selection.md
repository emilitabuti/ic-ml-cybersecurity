# 00 — Seleção da fonte

O fluxo principal utiliza exclusivamente o UNSW-NB15. A escolha decorre da
presença de `Stime` e `Ltime`, das três sessões naturais com ambas as classes e
da ocorrência dos nove tipos de ataque em treino, validação e teste.

Essas propriedades permitem separar um período futuro sem embaralhamento. A
tarefa executada é detecção binária do estado do tráfego; previsão antecipada
exige uma base com mais eventos independentes e não faz parte do artefato
servido.

O arquivo canônico de entrada é
`data/processed/unsw_nb15_cleaned_temporal.parquet`, não escalonado.
