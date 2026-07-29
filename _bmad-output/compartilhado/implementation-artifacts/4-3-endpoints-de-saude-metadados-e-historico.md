# Story 4.3: Endpoints de Saude, Metadados e Historico

Status: done

## Story

Como desenvolvedora do dashboard (Isabela),
Quero endpoints para verificar o estado da API, metadados do modelo ativo e historico de predicoes,
Para que o dashboard mostre informacoes do sistema e o analista possa acessar predicoes anteriores.

## Acceptance Criteria

1. **Dado** que a API esta rodando com modelo carregado
   **Quando** envio `GET /health`
   **Então** retorna HTTP 200 com status da API e nome do modelo carregado.

2. **Quando** envio `GET /model/info`
   **Então** retorna tipo de algoritmo, `window_size`, features utilizadas e data de treino/criacao do artefato.

3. **Quando** envio `GET /history`
   **Então** retorna lista das ultimas predicoes com timestamp, prediction, confidence e model.

4. **Dado** que a API inicializa
   **Quando** o modelo serializado e carregado
   **Então** o carregamento ocorre uma vez por processo e completa em ate 5s.

## Tasks / Subtasks

- [x] Task 1: Carregar modelo no startup da API (AC: #4)
  - [x] Subtask 1.1: Implementar `load_model_once()` no servico.
  - [x] Subtask 1.2: Conectar `load_model_once()` ao lifespan do FastAPI.
  - [x] Subtask 1.3: Medir tempo de carga e logar aviso acima de 5s.

- [x] Task 2: Implementar endpoints de metadados e historico (AC: #2, #3)
  - [x] Subtask 2.1: Implementar `GET /model/info`.
  - [x] Subtask 2.2: Implementar `GET /history`.
  - [x] Subtask 2.3: Manter buffer em memoria com `deque(maxlen=100)`.

- [x] Task 3: Alinhar health check ao contrato (AC: #1)
  - [x] Subtask 3.1: Preservar `status` e `version`.
  - [x] Subtask 3.2: Acrescentar `model` com o algoritmo carregado.
  - [x] Subtask 3.3: Cobrir o retorno em teste.

## Dev Notes

- O historico e intencionalmente em memoria por ser MVP local.
- `GET /history` registra apenas predicoes reais geradas por `POST /predict`.
- `uvicorn --reload` pode reiniciar o processo em mudancas de arquivo, mas o modelo nao e recarregado por request dentro do processo ativo.
- `GET /docs` continua disponivel automaticamente pelo FastAPI.

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-4.3]
- [Source: ml-pipeline/src/api/main.py]
- [Source: ml-pipeline/src/api/routes/predict.py]
- [Source: ml-pipeline/src/api/services/prediction_service.py]
- [Source: ml-pipeline/tests/test_api_predict_real.py]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `.venv/bin/python -m pytest -q tests/test_api_predict_real.py tests/test_api_predict_mock.py` -> `9 passed, 1 warning`.
- `.venv/bin/python -m pytest -q` -> `159 passed, 4 warnings`.
- Carga local do RF no startup/smoke: cerca de `2.10s`.
- Carga direta do RF: `1.897s`.

### Completion Notes List

- `GET /health` retorna `status`, `version` e `model`.
- `GET /model/info` retorna metadados do artefato carregado.
- `GET /history` retorna as ultimas predicoes reais armazenadas em `deque(maxlen=100)`.
- Startup carrega `models/model_rf.pkl` uma vez por processo via lifespan.

### File List

- `ml-pipeline/src/api/main.py`
- `ml-pipeline/src/api/routes/predict.py`
- `ml-pipeline/src/api/schemas/prediction.py`
- `ml-pipeline/src/api/services/prediction_service.py`
- `ml-pipeline/tests/test_api_predict_real.py`
- `_bmad-output/compartilhado/implementation-artifacts/4-3-endpoints-de-saude-metadados-e-historico.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-29

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado.
- Endpoint de saude agora atende o AC que pede o nome do modelo carregado.
- Historico tem capacidade minima de 100 predicoes conforme FR28 para o MVP local.
