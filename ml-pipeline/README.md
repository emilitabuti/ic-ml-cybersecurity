# Pipeline temporal de detecção — UNSW-NB15

Ele
avalia generalização temporal no UNSW-NB15, com seleção de atributos dentro dos
folds, purga nas fronteiras e uma sessão futura mantida fechada até a avaliação
final.

## Protocolo

- dataset: UNSW-NB15 não escalonado;
- tarefa: detecção binária do estado do último registro da janela;
- janela: 10 registros, isolada por partição, sessão e arquivo-fonte;
- desenvolvimento: 3 folds cronológicos expansivos, sem embaralhamento;
- pré-processamento e ranking: ajustados somente no treino de cada fold;
- candidatos: todos os atributos, `top_10`, `top_20` e `top_30`;
- configurações finais: Decision Tree `top_10`, LSTM `top_20` e Random Forest
  `top_30`;
- teste: sessão posterior, aberta uma única vez após o congelamento;
- artefato servido: Random Forest `top_30`.

O resultado final do Random Forest foi F1 `0,9261`, PR-AUC `0,9856`, precisão
`0,9010`, revocação `0,9525` e FPR `0,0094` em 306.701 janelas futuras.

## Instalação

Use Python 3.12, a mesma versão do ambiente final:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Fluxo de execução

Os datasets não são versionados. Coloque os Parquets brutos em
`data/raw/unsw_nb15/` e execute, a partir de `ml-pipeline/`:

```bash
python -m src.data.pipeline.collector
python -m src.data.pipeline.cleaner \
  --output-path data/processed/unsw_nb15_cleaned_temporal.parquet
python -m src.data.detection_temporal_splitter
python -m src.data.expanding_temporal_folds
python -m src.training.temporal_development_experiments
```

O protocolo congelado está em `reports_temporal/unsw/protocol.json`. A
avaliação final já consumiu a única abertura autorizada do teste e não deve ser
reexecutada. As rotinas abaixo existem para reprodução auditada em uma nova
base ou em um novo protocolo, não para reajustar o resultado publicado:

```bash
python -m src.training.temporal_final_evaluation
python -m src.training.temporal_final_reporting
python -m src.models.temporal_artifact_builder
```

## API

O único artefato aceito é `models/model_rf_temporal_v2.pkl`. A API recebe dez
registros com os 43 campos brutos, aplica pré-processamento, seleção `top_30`,
construção da janela e inferência.

```bash
uvicorn src.api.main:app --reload
```

Endpoints principais:

- `POST /predict`;
- `GET /health`;
- `GET /model/info`;
- `GET /history`.

## Verificação

```bash
python -m pytest tests -q
cd ..
python scripts/audit_final_documents.py
```

Os resultados publicados ficam em `reports_temporal/unsw/`.
