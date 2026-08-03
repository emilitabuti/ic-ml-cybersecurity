# Protocolo metodológico canônico

## Objetivo

Avaliar detecção binária de tráfego malicioso em uma sessão posterior do
UNSW-NB15. O rótulo corresponde ao último registro de uma janela de dez fluxos;
portanto, o artefato detecta o estado corrente com contexto recente.

## Dados e divisão

O pipeline parte de `unsw_nb15_cleaned_temporal.parquet`, preservando `Stime`,
`Ltime`, `source_file` e `record_id`. A ordenação estável identifica três
sessões naturais:

| Papel | Registros após purga |
|---|---:|
| Treino | 1.023.187 |
| Validação | 254.326 |
| Teste fechado | 306.710 |

Nove registros são purgados de cada lado das fronteiras. Nenhuma janela cruza
partição, sessão, bloco de desenvolvimento ou arquivo-fonte.

## Desenvolvimento

Três folds cronológicos expansivos são executados com `shuffle=False`. Em cada
fold, transformação logarítmica, one-hot, `RobustScaler` e ranking de
importância são ajustados somente no treino. Decision Tree, Random Forest e
LSTM são comparados com todas as variáveis e com `top_10`, `top_20` e `top_30`.

F1 médio é a métrica primária. As configurações congeladas foram:

- Decision Tree `top_10`;
- LSTM `top_20`;
- Random Forest `top_30`.

## Avaliação final

Os modelos são ajustados em treino+validação e avaliados juntos uma única vez
em 306.701 janelas do teste futuro. Não existe seleção, ajuste de limiar ou
refit no teste. O Random Forest `top_30` obteve F1 0,9261 e PR-AUC 0,9856.

O estado final registra uma leitura bruta e uma execução de avaliação. Uma nova
avaliação desse mesmo teste não é autorizada.

## Inferência

O único artefato servido é `models/model_rf_temporal_v2.pkl`. Ele recebe dez
registros com 43 campos brutos e aplica pré-processamento, seleção dos 30
atributos, janela achatada de 300 valores e Random Forest.

## Evidências

- `ml-pipeline/reports_temporal/unsw/protocol.json`;
- `ml-pipeline/reports_temporal/unsw/final_test_metrics.json`;
- `ml-pipeline/reports_temporal/unsw/tables/`;
- `docs/emili/relatorio-final/auditoria-final.md`.
