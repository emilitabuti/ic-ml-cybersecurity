# Story 3.6: Relatorio de Desempenho por Tipo de Ataque

Status: done

## Story

Como pesquisadora de IC (Emili),
Quero gerar um relatorio de desempenho dos modelos por tipo de ataque do CICIDS2017,
Para que o artigo cientifico apresente analise granular alem das metricas agregadas.

## Acceptance Criteria

1. **Dado** que os modelos foram avaliados
   **Quando** executo a geracao do relatorio em `evaluator.py`
   **Então** F1, Precision, Recall e FPR aparecem por tipo de ataque.

2. **Dado** que preciso incluir a analise no artigo
   **Quando** executo exportacao
   **Então** o relatorio sai em CSV e opcionalmente Markdown.

3. **Dado** que ha multiplos modelos
   **Quando** o relatorio e calculado
   **Então** melhor e pior modelo por tipo de ataque sao identificados por F1.

## Tasks / Subtasks

- [x] Task 1: Preservar tipo de ataque nas predicoes por fold (AC: #1)
  - [x] Subtask 1.1: Propagar `Attack_Type`/`label` ou fallback `Attack`.
  - [x] Subtask 1.2: Salvar `attack_type` no CSV de predicoes.

- [x] Task 2: Implementar relatorio granular (AC: #1-#3)
  - [x] Subtask 2.1: Ler `reports/predictions/*_fold_predictions.csv`.
  - [x] Subtask 2.2: Calcular metricas por ataque contra benignos.
  - [x] Subtask 2.3: Marcar `best_by_f1` e `worst_by_f1`.

- [x] Task 3: Exportar e validar (AC: #2-#3)
  - [x] Subtask 3.1: Criar export CSV.
  - [x] Subtask 3.2: Criar export Markdown opcional.
  - [x] Subtask 3.3: Testar ranking melhor/pior.

## Dev Notes

- Para modelos binarios, o relatorio por ataque interpreta cada tipo como positivo contra amostras benignas, usando a predicao binaria de ataque.
- Tipos benignos (`BENIGN`, `NORMAL`) sao excluidos da lista de ataques.
- Nenhum endpoint ou serializacao real de modelo foi implementado.

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-3.6]
- [Source: ml-pipeline/src/training/evaluator.py]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `.venv/bin/python -m pytest tests/test_evaluator.py -q` — passed in bateria agregada.

### Completion Notes List

- Relatorio por tipo de ataque implementado em `evaluator.py`.
- Exportacao CSV e Markdown disponivel por CLI.
- Melhor/pior modelo por ataque marcado por `detection_rank`.

### File List

- `ml-pipeline/src/training/evaluator.py`
- `ml-pipeline/src/training/cross_validation.py`
- `ml-pipeline/src/training/data_preparation.py`
- `ml-pipeline/tests/test_evaluator.py`
- `_bmad-output/compartilhado/implementation-artifacts/3-6-relatorio-de-desempenho-por-tipo-de-ataque.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-25

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado.
- Relatorio granular usa os CSVs de predicoes gerados pelos treinos.
- Ranking melhor/pior por ataque esta coberto por teste.
- Escopo do Epic 4 permanece intacto.
