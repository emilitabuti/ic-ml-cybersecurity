# Cenario simulado de SYN flood com dados tabulares sinteticos

Este diretorio contem um estudo de caso delimitado para a IC da Isabela:
detectar um cenario simulado de DDoS/SYN flood usando dados tabulares
sinteticos.

O experimento nao deve ser chamado de ataque adversarial, porque a amostra nao
esta tentando enganar um modelo real de Machine Learning. Como o modelo real
ainda nao esta integrado, a classificacao e feita por uma heuristica temporaria,
usada apenas para simular a etapa que futuramente sera realizada pelo modelo.

## Onde esta o codigo

Este diretorio fica apenas com a documentacao do cenario. Os scripts
executaveis foram movidos para o componente Python, seguindo a arquitetura do
repositorio:

`ml-pipeline/src/evaluation/scenarios/`

Os resultados pequenos versionados ficam em:

`ml-pipeline/reports/isabela/syn_flood/`

## O que o codigo gera

- Trafego normal para comparacao.
- SYN flood de baixa intensidade.
- SYN flood de media intensidade.
- SYN flood de alta intensidade.
- Varias amostras de cada grupo.
- Metricas quantitativas de avaliacao.
- Eventos no contrato atual do dashboard: `prediction`, `confidence`, `model` e
  `timestamp`.

## Arquivos principais

- `ml-pipeline/src/evaluation/scenarios/generate_syn_flood_dataset.py`: gera o
  CSV sintetico com varias amostras.
- `ml-pipeline/src/evaluation/scenarios/evaluate_syn_flood_scenario.py`: aplica a
  heuristica, calcula metricas e gera eventos para o dashboard.
- `ml-pipeline/src/evaluation/scenarios/send_real_predictions_to_api.py`: chama
  a API real em `POST /predict` e popula `GET /history` sem mock.
- `EXPLICACAO_DO_CENARIO.md`: texto detalhado para relatorio/apresentacao.

## Saidas geradas

- `ml-pipeline/reports/isabela/syn_flood/sandbox_tabular_dataset/syn_flood_synthetic_samples.csv`
- `ml-pipeline/reports/isabela/syn_flood/evaluation_results.csv`
- `ml-pipeline/reports/isabela/syn_flood/evaluation_summary.json`
- `ml-pipeline/reports/isabela/syn_flood/dashboard_history_events.json`

## Como executar

```powershell
cd C:\Users\isagr\Documents\ic-ml-cybersecurity\ml-pipeline
py -m src.evaluation.scenarios.generate_syn_flood_dataset --samples-per-group 30 --overwrite
py -m src.evaluation.scenarios.evaluate_syn_flood_scenario
```

Com `30` amostras por grupo, o experimento gera `120` amostras no total:

- 30 normais;
- 30 SYN flood baixo;
- 30 SYN flood medio;
- 30 SYN flood alto.

## Como aparecer no dashboard com a API real

O dashboard nao le CSV diretamente. Ele consome `GET /history` da API. No fluxo
integrado atual, `GET /history` e real: ele mostra as predicoes registradas
quando alguem chama `POST /predict`.

Para alimentar o dashboard sem mock, rode a API real e depois envie janelas
sinteticas para `POST /predict`:

Na raiz do repositorio:

```powershell
cd .\ml-pipeline
uvicorn src.api.main:app --reload
```

Em outro terminal:

```powershell
cd C:\Users\isagr\Documents\ic-ml-cybersecurity
cd .\ml-pipeline
py -m src.evaluation.scenarios.send_real_predictions_to_api --limit 20
```

Depois, inicie o dashboard normalmente. O polling de `GET /history` passa a
receber as respostas reais produzidas pelo modelo carregado na API.

## Metricas coletadas

O arquivo `ml-pipeline/reports/isabela/syn_flood/evaluation_summary.json`
registra:

- quantidade de amostras analisadas;
- quantidade corretamente identificada;
- verdadeiros positivos;
- verdadeiros negativos;
- falsos positivos;
- falsos negativos;
- acuracia;
- tempo medio de resposta;
- confianca media por grupo;
- severidade exibida por grupo.
