# Story 2.2: Transformação em Sliding Window

Status: done

## Story

Como pesquisadora de ML (Emili),
Quero transformar sequências de registros de tráfego em janelas deslizantes de tamanho N configurável,
Para que os modelos sequenciais capturem dependências temporais que precedem ataques e os modelos tabulares recebam uma representação achatada consistente.

## Acceptance Criteria

1. **Dado** que o conjunto de treino tem as features selecionadas (Story 2.1)
   **Quando** executo `feature_engineer.py` com `WINDOW_SIZE=N`, onde `N ∈ {5, 10, 20}`
   **Então** cada amostra resultante é uma janela de N registros consecutivos.

2. **Dado** que janelas foram geradas
   **Quando** verifico os labels
   **Então** o label de cada janela é o label do último registro da janela.

3. **Dado** que treino e teste já foram separados
   **Quando** aplico sliding window
   **Então** a transformação é aplicada separadamente sobre treino e teste, sem compartilhamento de registros ou índices entre conjuntos.

4. **Dado** que `WINDOW_SIZE=10`
   **Quando** verifico as dimensões
   **Então** cada amostra sequencial tem shape `(10, num_features)` para LSTM e cada amostra tabular tem shape `(10 * num_features,)` para RF/DT.

5. **Dado** que o tamanho da janela não foi informado
   **Quando** gero janelas
   **Então** o valor é lido de `config.WINDOW_SIZE`, sem hardcode.

## Tasks / Subtasks

- [x] Task 1: Escrever testes TDD para sliding window (AC: #1-#5)
  - [x] Subtask 1.1: Criar `tests/test_sliding_window.py` com dados sintéticos sequenciais.
  - [x] Subtask 1.2: Testar quantidade de janelas e conteúdo consecutivo.
  - [x] Subtask 1.3: Testar label como último registro da janela.
  - [x] Subtask 1.4: Testar shapes 3D para LSTM e achatado para RF/DT.
  - [x] Subtask 1.5: Testar aplicação separada em treino/teste usando índices originais disjuntos.

- [x] Task 2: Implementar `src/features/feature_engineer.py` (AC: #1-#5)
  - [x] Subtask 2.1: Criar `SlidingWindowResult` com `X`, `y` e `window_indices`.
  - [x] Subtask 2.2: Implementar `create_sliding_windows(X, y, window_size=None, flatten=False, indices=None)`.
  - [x] Subtask 2.3: Implementar `create_train_test_windows(...)` aplicando a transformação separadamente.
  - [x] Subtask 2.4: Validar `WINDOW_SIZE` permitido (`5`, `10`, `20`) e inputs incompatíveis.
  - [x] Subtask 2.5: Usar `logging.getLogger(__name__)`, type hints e mensagens de erro descritivas.

- [x] Task 3: Validar e documentar a story (AC: todos)
  - [x] Subtask 3.1: Rodar `pytest tests/test_sliding_window.py -v`.
  - [x] Subtask 3.2: Rodar `pytest tests/` no `ml-pipeline`.
  - [x] Subtask 3.3: Atualizar Dev Agent Record e File List.

## Dev Notes

### Contexto existente

- Story 1.4 implementou split estratificado antes de qualquer transformação.
- Story 2.1 implementou `RandomForestFeatureSelector`; sliding window deve receber `X_train_selected` e `X_test_selected`, não recalcular seleção.
- `config.WINDOW_SIZE` já existe e tem default `10`.

### Regras obrigatórias

- Nunca criar janelas cruzando treino e teste. A API deve ter função explícita para aplicar em separado.
- O label da janela é sempre `y[end_index]`, ou seja, o último registro dentro da janela.
- `window_indices` deve preservar os índices originais quando `indices` for fornecido, permitindo auditoria anti-leakage na Story 2.3.
- Para LSTM, `X` fica em 3D: `(n_windows, window_size, n_features)`.
- Para RF/DT, `X` fica em 2D achatado: `(n_windows, window_size * n_features)`.
- Não implementar Epic 3: sem treino de RF/DT/LSTM e sem MLflow.

### Interface esperada

```python
from src.features.feature_engineer import create_train_test_windows

train_windows, test_windows = create_train_test_windows(
    X_train_selected,
    y_train,
    X_test_selected,
    y_test,
    train_indices=train_indices,
    test_indices=test_indices,
)

X_lstm = train_windows.X
X_rf = train_windows.flatten().X
```

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-2.2] — ACs oficiais da story.
- [Source: _bmad-output/compartilhado/planning-artifacts/architecture.md#Streaming-vs.-Batch-Processing] — batch com sliding window.
- [Source: _bmad-output/compartilhado/planning-artifacts/architecture.md#Data-Architecture] — leakage prevention após split train/test.
- [Source: _bmad-output/compartilhado/implementation-artifacts/2-1-feature-selection-sobre-o-conjunto-de-treino.md] — saída esperada da seleção de features.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `.venv/bin/python -m pytest tests/test_sliding_window.py -v` — 11 passed.
- `.venv/bin/python -m pytest tests/` — 134 passed, 1 warning de depreciação Starlette/httpx.

### Completion Notes List

- Implementado `SlidingWindowResult` com `X`, `y`, `window_indices` e método `flatten()`.
- Implementado `create_sliding_windows()` com label do último registro, validação de `WINDOW_SIZE ∈ {5, 10, 20}` e suporte a índices originais.
- Implementado `create_train_test_windows()` para aplicar a transformação separadamente em treino e teste.

### File List

- `ml-pipeline/src/features/__init__.py`
- `ml-pipeline/src/features/feature_engineer.py`
- `ml-pipeline/tests/test_sliding_window.py`
- `_bmad-output/compartilhado/implementation-artifacts/2-2-transformacao-em-sliding-window.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-25

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado. A implementação satisfaz os ACs da Story 2.2.
- `create_sliding_windows()` gera janelas consecutivas, usa label do último registro e respeita `config.WINDOW_SIZE` quando não informado.
- `create_train_test_windows()` aplica a transformação separadamente em treino e teste; `window_indices` preserva rastreabilidade para auditoria anti-leakage.
- Representações sequencial `(N, window_size, num_features)` e tabular `(N, window_size * num_features)` cobertas por testes.
- Escopo preservado: nenhum código de Epic 3, MLflow ou treino final de modelos foi adicionado.

Validation:

- `git diff --check` — sem problemas.
- `.venv/bin/python -m pytest tests/test_sliding_window.py -v` — 11 passed.
- `.venv/bin/python -m pytest tests/` — 134 passed, 1 warning de depreciação Starlette/httpx.
