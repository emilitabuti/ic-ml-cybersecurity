# Story 2.3: Validação Anti-Leakage do Pipeline de Features

Status: done

## Story

Como pesquisadora de IC,
Quero validar que o pipeline de features não vaza dados do teste para o treino,
Para que a validade metodológica do experimento e a publicabilidade do artigo sejam garantidas.

## Acceptance Criteria

1. **Dado** que o pipeline de feature engineering foi executado (Stories 2.1 e 2.2)
   **Quando** executo `tests/test_feature_engineer.py`
   **Então** nenhum índice do conjunto de teste aparece em janelas do conjunto de treino.

2. **Dado** que feature selection foi executada
   **Quando** verifico os metadados e o artefato persistido
   **Então** os parâmetros de seleção (importâncias, top-N/threshold e seleção final) foram calculados apenas com dados de treino.

3. **Dado** que a seleção foi ajustada com treino
   **Quando** transformo o teste
   **Então** o teste usa a seleção já calculada, sem refit e sem recalcular importâncias.

4. **Dado** que executo a suíte de validação
   **Quando** todos os testes terminam
   **Então** o resultado é PASS, sem exceções e sem regressões na suíte completa.

## Tasks / Subtasks

- [x] Task 1: Criar testes anti-leakage integrados (AC: #1-#4)
  - [x] Subtask 1.1: Criar `tests/test_feature_engineer.py`.
  - [x] Subtask 1.2: Testar split -> feature selection -> sliding window com índices originais disjuntos.
  - [x] Subtask 1.3: Testar que janelas de treino não contêm nenhum índice do teste.
  - [x] Subtask 1.4: Testar que metadados/artefato de feature selection registram apenas amostras de treino.
  - [x] Subtask 1.5: Testar que `transform(X_test)` não cria RandomForest nem chama `fit()`.

- [x] Task 2: Ajustar implementação somente se a validação revelar lacunas (AC: #1-#4)
  - [x] Subtask 2.1: Reusar `RandomForestFeatureSelector`; não duplicar seleção.
  - [x] Subtask 2.2: Reusar `create_train_test_windows`; não criar janelas com dataset concatenado.
  - [x] Subtask 2.3: Manter `window_indices` como evidência auditável de ausência de leakage.

- [x] Task 3: Validar e documentar a story (AC: todos)
  - [x] Subtask 3.1: Rodar `pytest tests/test_feature_engineer.py -v`.
  - [x] Subtask 3.2: Rodar `pytest tests/` no `ml-pipeline`.
  - [x] Subtask 3.3: Atualizar Dev Agent Record e File List.

## Dev Notes

### Contexto existente

- Story 2.1: `RandomForestFeatureSelector` calcula importâncias com RF sobre `fit(X_train, y_train)`, persiste JSON e aplica `transform()` sem refit.
- Story 2.2: `create_train_test_windows()` aplica janelas separadamente e preserva `window_indices`.
- Story 1.4: `split_train_test()` garante split estratificado antes das transformações.

### Estratégia de validação

- Usar dados sintéticos; sem dependência de `data/processed/`.
- Usar uma coluna identificadora original para reconstruir índices após `split_train_test()`.
- Passar `train_indices` e `test_indices` explicitamente para `create_train_test_windows()`.
- Inspecionar `window_indices` para provar que janelas de treino e teste são disjuntas.
- Inspecionar o artefato JSON da Story 2.1 para provar que `n_training_samples` corresponde só a treino.
- Usar monkeypatch em `RandomForestClassifier` antes de `transform(X_test)` para falhar se houver refit/recalculo.

### O que NÃO fazer

- Não implementar MLflow, treino de RF/DT/LSTM, avaliação de modelo ou Epic 3.
- Não alterar o contrato de dados do Epic 1.
- Não criar um segundo seletor ou um segundo transformador de janelas.

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-2.3] — ACs oficiais da story.
- [Source: _bmad-output/compartilhado/implementation-artifacts/2-1-feature-selection-sobre-o-conjunto-de-treino.md] — feature selection train-only.
- [Source: _bmad-output/compartilhado/implementation-artifacts/2-2-transformacao-em-sliding-window.md] — sliding window separado com `window_indices`.
- [Source: _bmad-output/compartilhado/planning-artifacts/architecture.md#Data-Architecture] — leakage prevention após split.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `.venv/bin/python -m pytest tests/test_feature_engineer.py -v` — 3 passed.
- `.venv/bin/python -m pytest tests/` — 137 passed, 1 warning de depreciação Starlette/httpx.

### Completion Notes List

- Criado `tests/test_feature_engineer.py` com validação anti-leakage integrada do pipeline split -> feature selection -> sliding window.
- Confirmado que nenhum índice de teste aparece em janelas de treino.
- Confirmado que metadados e artefato de feature selection refletem apenas amostras de treino.
- Confirmado que `transform(X_test)` não instancia Random Forest nem recalcula importâncias.

### File List

- `ml-pipeline/tests/test_feature_engineer.py`
- `_bmad-output/compartilhado/implementation-artifacts/2-3-validacao-anti-leakage-do-pipeline-de-features.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-25

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado. A validação satisfaz os ACs da Story 2.3.
- O teste integrado exercita split -> feature selection -> sliding window e comprova que índices de teste não aparecem em janelas de treino.
- O artefato de feature selection é verificado com `n_training_samples` igual apenas ao treino, não treino + teste.
- `transform(X_test)` é protegido por monkeypatch para falhar se houver instanciação de Random Forest/recalculo de importâncias.
- Escopo preservado: nenhum código de Epic 3, MLflow ou treino final de modelos foi adicionado.

Validation:

- `git diff --check` — sem problemas.
- `.venv/bin/python -m pytest tests/test_feature_engineer.py -v` — 3 passed.
- `.venv/bin/python -m pytest tests/` — 137 passed, 1 warning de depreciação Starlette/httpx.
