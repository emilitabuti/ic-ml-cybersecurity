# Story 2.1: Feature Selection sobre o Conjunto de Treino

Status: done

## Story

Como pesquisadora de ML (Emili),
Quero executar feature selection sobre o conjunto de treino para selecionar as top-N features mais relevantes,
Para que o modelo treine com as features de maior poder preditivo, reduzindo ruído e dimensionalidade sem data leakage.

## Acceptance Criteria

1. **Dado** que o dataset foi dividido em treino e teste (Story 1.4)
   **Quando** executo `feature_selector.py` com N e threshold configuráveis
   **Então** a importância das features é calculada com Random Forest exclusivamente sobre `X_train`/`y_train`.

2. **Dado** que o seletor foi ajustado sobre treino
   **Quando** seleciono features
   **Então** são selecionadas as top-N features por importância ou todas as features com importância acima do threshold mínimo configurável.

3. **Dado** que a seleção foi calculada
   **Quando** aplico a transformação em treino e teste
   **Então** a mesma lista persistida de features é usada nos dois conjuntos, sem recalcular importância no teste.

4. **Dado** que executo feature selection duas vezes com o mesmo seed
   **Quando** comparo o conjunto de features selecionadas e suas importâncias
   **Então** o resultado é idêntico nas duas execuções.

5. **Dado** que a seleção foi concluída
   **Quando** verifico o artefato persistido
   **Então** ele contém nomes/índices das features selecionadas, importâncias, parâmetros usados (`top_n`, `threshold`, `random_state`) e metadados de treino (`n_training_samples`, `n_input_features`).

## Tasks / Subtasks

- [x] Task 1: Escrever testes TDD para feature selection (AC: #1-#5)
  - [x] Subtask 1.1: Criar `tests/test_feature_selector.py` com dados sintéticos e nomes de features.
  - [x] Subtask 1.2: Testar seleção top-N determinística com `config.RANDOM_SEED`.
  - [x] Subtask 1.3: Testar seleção por threshold mínimo.
  - [x] Subtask 1.4: Testar persistência e recarga do artefato JSON.
  - [x] Subtask 1.5: Testar que `transform()` não chama `fit()` nem recalcula importância no teste.

- [x] Task 2: Implementar `src/features/feature_selector.py` (AC: #1-#5)
  - [x] Subtask 2.1: Criar classe `RandomForestFeatureSelector` com `fit`, `transform`, `fit_transform`, `save` e `load`.
  - [x] Subtask 2.2: Usar `sklearn.ensemble.RandomForestClassifier` com `random_state=config.RANDOM_SEED`.
  - [x] Subtask 2.3: Validar parâmetros (`top_n >= 1`, `threshold >= 0`, ao menos um critério ativo).
  - [x] Subtask 2.4: Persistir seleção em JSON em caminho configurável, sem depender de MLflow ou treino de modelos.
  - [x] Subtask 2.5: Usar `logging.getLogger(__name__)`, type hints e mensagens de erro descritivas.

- [x] Task 3: Adicionar configuração centralizada (AC: #2, #5)
  - [x] Subtask 3.1: Adicionar `FEATURE_SELECTION_TOP_N` ao `config.py`, default `20`.
  - [x] Subtask 3.2: Adicionar `FEATURE_SELECTION_THRESHOLD` ao `config.py`, default `0.0`.
  - [x] Subtask 3.3: Adicionar `FEATURE_SELECTION_ARTIFACT_PATH` ao `config.py`, default `models/feature_selection.json`.

- [x] Task 4: Validar e documentar a story (AC: todos)
  - [x] Subtask 4.1: Rodar `pytest tests/test_feature_selector.py -v`.
  - [x] Subtask 4.2: Rodar `pytest tests/` no `ml-pipeline`.
  - [x] Subtask 4.3: Atualizar Dev Agent Record e File List.

## Dev Notes

### Contexto existente

- Story 1.4 implementou `src/data/data_splitter.py::split_train_test(X, y)` com `train_test_split(..., stratify=y, random_state=config.RANDOM_SEED)`.
- O fluxo obrigatório é: `load_binary_dataset()` -> `split_train_test()` -> `feature_selector.fit(X_train, y_train)` -> `transform(X_train)` e `transform(X_test)`.
- `src/features/` existe, mas contém apenas `__init__.py`.
- `requirements.txt` já fixa `scikit-learn==1.8.0`, `numpy`, `joblib` e `pytest`.

### Regras arquiteturais obrigatórias

- Feature selection deve ocorrer após o split e apenas sobre treino. Nunca aceitar `X_test`/`y_test` em `fit()`.
- Transformação de teste deve usar somente `selected_indices_`/`selected_feature_names_` já persistidos ou carregados.
- Usar `config.RANDOM_SEED`, nunca `random_state=42` hardcoded.
- Centralizar novos defaults em `config.py`; sem magic numbers espalhados.
- Usar `logging`, type hints e dados sintéticos nos testes.
- Não implementar Epic 3: sem MLflow, sem `src/training/`, sem treinamento final de RF/DT/LSTM.

### Interface esperada

```python
from src.features.feature_selector import RandomForestFeatureSelector

selector = RandomForestFeatureSelector(
    feature_names=feature_names,
    top_n=config.FEATURE_SELECTION_TOP_N,
    threshold=config.FEATURE_SELECTION_THRESHOLD,
)
X_train_selected = selector.fit_transform(X_train, y_train)
X_test_selected = selector.transform(X_test)
selector.save()

loaded = RandomForestFeatureSelector.load("models/feature_selection.json")
X_test_selected_again = loaded.transform(X_test)
```

### Persistência esperada

O JSON deve conter ao menos:

- `selected_feature_names`
- `selected_indices`
- `feature_importances`
- `top_n`
- `threshold`
- `random_state`
- `n_training_samples`
- `n_input_features`

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-2.1] — ACs oficiais da story.
- [Source: _bmad-output/compartilhado/planning-artifacts/architecture.md#ML-Pipeline-Patterns] — `RANDOM_SEED=42`, scikit-learn e reprodutibilidade.
- [Source: _bmad-output/compartilhado/planning-artifacts/architecture.md#Enforcement-Guidelines] — logging, config centralizada e anti-patterns.
- [Source: _bmad-output/compartilhado/implementation-artifacts/1-4-divisao-train-test-estratificada-e-formalizacao-do-contrato-de-dados.md] — split antes de qualquer transformação.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `pytest tests/test_feature_selector.py -v` com Python global falhou por ausência de dependências no interpretador fora da `.venv`; validação oficial executada com `.venv/bin/python`.
- `.venv/bin/python -m pytest tests/test_feature_selector.py -v` — 9 passed.
- `.venv/bin/python -m pytest tests/` — 123 passed, 1 warning de depreciação Starlette/httpx existente.

### Completion Notes List

- Implementado `RandomForestFeatureSelector` com fit exclusivo sobre treino, transform sem refit, seleção top-N ou threshold, persistência JSON e load sem treinar.
- Adicionadas configurações `FEATURE_SELECTION_TOP_N`, `FEATURE_SELECTION_THRESHOLD` e `FEATURE_SELECTION_ARTIFACT_PATH`.
- `config.py` agora tolera ausência de `python-dotenv` no interpretador, mantendo `load_dotenv()` quando disponível.

### File List

- `ml-pipeline/config.py`
- `ml-pipeline/src/features/__init__.py`
- `ml-pipeline/src/features/feature_selector.py`
- `ml-pipeline/tests/test_feature_selector.py`
- `_bmad-output/compartilhado/implementation-artifacts/2-1-feature-selection-sobre-o-conjunto-de-treino.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-25

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado. A implementação satisfaz os ACs da Story 2.1.
- `fit()` recebe apenas `X`/`y` de treino e registra `n_training_samples`; `transform()` usa somente `selected_indices_` já calculado/carregado.
- Persistência JSON cobre features selecionadas, índices, importâncias, parâmetros e metadados de treino.
- Escopo preservado: nenhum código de Epic 3, MLflow ou treino final de modelos foi adicionado.

Validation:

- `git diff --check` — sem problemas.
- `.venv/bin/python -m pytest tests/test_feature_selector.py -v` — 9 passed.
- `.venv/bin/python -m pytest tests/` — 123 passed, 1 warning de depreciação Starlette/httpx.
