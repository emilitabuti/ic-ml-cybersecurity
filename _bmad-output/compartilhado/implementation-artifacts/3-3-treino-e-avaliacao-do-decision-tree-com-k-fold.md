# Story 3.3: Treino e Avaliacao do Decision Tree com k-fold

Status: done

## Story

Como pesquisadora de ML (Emili),
Quero treinar o Decision Tree com k-fold k=5 nas mesmas condicoes do RF,
Para que a comparacao entre algoritmos seja metodologicamente valida.

## Acceptance Criteria

1. **Dado** que RF ja usa split k-fold padronizado
   **Quando** executo `train_dt.py`
   **Então** o DT usa o mesmo `StratifiedKFold`, seed e features.

2. **Dado** que cada fold termina
   **Quando** a avaliacao roda
   **Então** F1, AUC-ROC, Precision, Recall e FPR sao calculados e registrados.

3. **Dado** que MLflow esta ativo
   **Quando** executo `train_dt.py`
   **Então** o experimento se chama `ic-ml-cybersecurity-decision_tree`.

## Tasks / Subtasks

- [x] Task 1: Implementar `train_dt.py` (AC: #1-#3)
  - [x] Subtask 1.1: Criar factory `build_decision_tree()`.
  - [x] Subtask 1.2: Reusar `run_sklearn_cross_validation()`.
  - [x] Subtask 1.3: Usar `random_state=config.RANDOM_SEED`.

- [x] Task 2: Garantir comparabilidade RF x DT (AC: #1)
  - [x] Subtask 2.1: Testar que RF e DT compartilham splits identicos.
  - [x] Subtask 2.2: Usar a mesma preparacao de dados em `PreparedDataset`.

- [x] Task 3: Validar (AC: todos)
  - [x] Subtask 3.1: Rodar testes de cross-validation.

## Dev Notes

- O DT usa o mesmo helper do RF; a unica diferenca e a factory de modelo.
- A escolha evita divergencia metodologica entre scripts.

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-3.3]
- [Source: _bmad-output/compartilhado/implementation-artifacts/3-2-treino-e-avaliacao-do-random-forest-com-k-fold.md]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `.venv/bin/python -m pytest tests/test_training_cross_validation.py -q` — passed in bateria agregada.

### Completion Notes List

- `train_dt.py` implementado usando o mesmo split/seed/features do RF.
- Experimento MLflow padronizado como `decision_tree`.
- Resultados exportados em JSON/CSV no mesmo contrato do RF.

### File List

- `ml-pipeline/src/training/train_dt.py`
- `ml-pipeline/src/training/cross_validation.py`
- `ml-pipeline/tests/test_training_cross_validation.py`
- `_bmad-output/compartilhado/implementation-artifacts/3-3-treino-e-avaliacao-do-decision-tree-com-k-fold.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-25

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado.
- DT reaproveita exatamente o splitter do RF.
- Nome de experimento atende a story.
- Metricas e exportacoes seguem o contrato comum.
