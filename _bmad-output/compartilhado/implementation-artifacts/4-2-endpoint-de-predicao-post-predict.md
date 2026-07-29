# Story 4.2: Endpoint de Predicao POST /predict

Status: done

## Story

Como sistema de alertas da Isabela,
Quero enviar uma janela de trafego via HTTP e receber a predicao do modelo,
Para que o dashboard exiba alertas em tempo real com tipo de ameaca e nivel de confianca.

## Acceptance Criteria

1. **Dado** que a API esta rodando com modelo carregado
   **Quando** envio `POST /predict` com JSON contendo as features da janela
   **Então** a resposta retorna em ate 10s com `prediction`, `confidence`, `model` e `timestamp`.

2. **Dado** que envio features invalidas
   **Quando** a API valida colunas ou tipos
   **Então** retorna HTTP 422 com `{"detail": "...", "code": "INVALID_FEATURES"}`.

3. **Dado** que a API recebe multiplas requisicoes
   **Quando** executa inferencia
   **Então** o modelo nao e recarregado por request.

## Tasks / Subtasks

- [x] Task 1: Criar camada de servico para inferencia real (AC: #1, #3)
  - [x] Subtask 1.1: Implementar `prediction_service.py` com estado de artefato em memoria.
  - [x] Subtask 1.2: Usar `predict_from_artifact()` para aplicar scaler e sliding window.
  - [x] Subtask 1.3: Retornar resposta no contrato REST com timestamp ISO 8601.

- [x] Task 2: Validar payload de features (AC: #2)
  - [x] Subtask 2.1: Aceitar payload com `features` em lista de objetos.
  - [x] Subtask 2.2: Validar features ausentes, tipos nao numericos, valores nao finitos e janela insuficiente.
  - [x] Subtask 2.3: Mapear `InvalidFeaturesError` para HTTP 422.

- [x] Task 3: Expor rota FastAPI e testar (AC: #1-#3)
  - [x] Subtask 3.1: Implementar `POST /predict` em `src/api/routes/predict.py`.
  - [x] Subtask 3.2: Adicionar schemas Pydantic compartilhados.
  - [x] Subtask 3.3: Adicionar testes de predicao valida e erro 422.

## Dev Notes

- O endpoint usa resposta direta, sem envelope.
- Campos JSON permanecem em `snake_case`.
- Excecoes tipadas: `PredictionError`, `ModelNotLoadedError`, `InvalidFeaturesError`.
- O modelo e carregado no startup pela Story 4.3; esta story consome o artefato ja carregado.

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-4.2]
- [Source: ml-pipeline/src/api/routes/predict.py]
- [Source: ml-pipeline/src/api/services/prediction_service.py]
- [Source: ml-pipeline/tests/test_api_predict_real.py]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `.venv/bin/python -m pytest -q tests/test_api_predict_real.py tests/test_api_predict_mock.py` -> `8 passed, 1 warning`.
- `.venv/bin/python -m pytest -q` -> `159 passed, 4 warnings`.
- Smoke real com `models/model_rf.pkl`: `POST /predict` retornou HTTP 200, `model=random_forest`, `confidence=0.969999...`.

### Completion Notes List

- `POST /predict` real implementado.
- Validacao de features retorna HTTP 422 com codigo `INVALID_FEATURES`.
- Inferencia usa o pipeline completo embutido no artefato serializado.
- Predicoes sao registradas no historico em memoria para a Story 4.3.

### File List

- `ml-pipeline/src/api/routes/predict.py`
- `ml-pipeline/src/api/schemas/prediction.py`
- `ml-pipeline/src/api/services/prediction_service.py`
- `ml-pipeline/tests/test_api_predict_real.py`
- `_bmad-output/compartilhado/implementation-artifacts/4-2-endpoint-de-predicao-post-predict.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-29

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado.
- O contrato REST foi implementado com campos `snake_case`, timestamp ISO 8601 e erro tipado para features invalidas.
- Testes cobrem predicao valida e falha de validacao.
