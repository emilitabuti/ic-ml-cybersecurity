# Story 3.5: Tabela Comparativa de Metricas e Exportacao CSV

Status: done

## Story

Como pesquisadora de IC (Emili),
Quero gerar a tabela comparativa de desempenho entre RF, DT e LSTM e exporta-la em CSV,
Para que tenha a evidencia empirica central do artigo cientifico formatada para publicacao.

## Acceptance Criteria

1. **Dado** que RF, DT e LSTM/MLP foram avaliados
   **Quando** executo `evaluator.py`
   **Então** uma tabela RF x DT x LSTM e gerada.

2. **Dado** que a tabela foi gerada
   **Quando** verifico as colunas
   **Então** F1, AUC-ROC, Precision, Recall e FPR aparecem como media +/- desvio padrao.

3. **Dado** que ha modelos comparaveis
   **Quando** a tabela e montada
   **Então** o melhor modelo por metrica fica destacado em `best_metrics`.

4. **Dado** que preciso escrever o artigo
   **Quando** executo exportacao
   **Então** o CSV e compativel com importacao em LaTeX/Word.

## Tasks / Subtasks

- [x] Task 1: Implementar tabela comparativa (AC: #1-#3)
  - [x] Subtask 1.1: Ler `reports/metrics/*_metrics.json`.
  - [x] Subtask 1.2: Formatar media +/- desvio padrao.
  - [x] Subtask 1.3: Destacar melhores metricas, invertendo criterio para FPR.

- [x] Task 2: Exportar CSV (AC: #4)
  - [x] Subtask 2.1: Criar `export_comparison_csv()`.
  - [x] Subtask 2.2: Expor CLI em `evaluator.py`.

- [x] Task 3: Testar (AC: todos)
  - [x] Subtask 3.1: Testar destaque por F1 e FPR.
  - [x] Subtask 3.2: Testar CSV simples.

## Dev Notes

- A tabela le JSON gerado pelos scripts de treino; nao depende diretamente do MLflow UI para ser reprodutivel em testes.
- FPR usa menor valor como melhor modelo.

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-3.5]
- [Source: _bmad-output/compartilhado/implementation-artifacts/3-2-treino-e-avaliacao-do-random-forest-com-k-fold.md]
- [Source: _bmad-output/compartilhado/implementation-artifacts/3-3-treino-e-avaliacao-do-decision-tree-com-k-fold.md]
- [Source: _bmad-output/compartilhado/implementation-artifacts/3-4-treino-e-avaliacao-do-lstm-mlp-com-k-fold.md]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `.venv/bin/python -m pytest tests/test_evaluator.py -q` — passed in bateria agregada.

### Completion Notes List

- `evaluator.py` gera tabela comparativa e CSV.
- Melhor modelo por metrica destacado por coluna `best_metrics`.
- CSV sem markup pesado para compatibilidade com LaTeX/Word.

### File List

- `ml-pipeline/src/training/evaluator.py`
- `ml-pipeline/tests/test_evaluator.py`
- `ml-pipeline/README.md`
- `_bmad-output/compartilhado/implementation-artifacts/3-5-tabela-comparativa-de-metricas-e-exportacao-csv.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-25

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado.
- Comparacao suporta RF, DT e LSTM/MLP pelo mesmo contrato de JSON.
- FPR usa ranking correto.
- Exportacao CSV e simples e portavel.
