# Story 3.2: Treino e Avaliacao do Random Forest com k-fold

Status: done

## Story

Como pesquisadora de ML (Emili),
Quero treinar o Random Forest com k-fold k=5 e registrar todas as metricas cientificas no MLflow,
Para que tenha evidencia empirica replicavel do desempenho do RF para o artigo.

## Acceptance Criteria

1. **Dado** que os dados com sliding window estao prontos
   **Quando** executo `train_rf.py`
   **Então** o RF e treinado com k-fold k=5 e `random_state=config.RANDOM_SEED`.

2. **Dado** que cada fold termina
   **Quando** a avaliacao roda
   **Então** F1, AUC-ROC, Precision, Recall e FPR sao calculados por fold.

3. **Dado** que MLflow esta configurado
   **Quando** executo o treino
   **Então** algoritmo, hiperparametros, `WINDOW_SIZE` e metricas sao registrados.

4. **Dado** que todos os folds terminam
   **Quando** o resultado e exibido/exportado
   **Então** cada metrica aparece como media +/- desvio padrao.

## Tasks / Subtasks

- [x] Task 1: Implementar `train_rf.py` (AC: #1-#4)
  - [x] Subtask 1.1: Criar factory `build_random_forest()`.
  - [x] Subtask 1.2: Usar `RANDOM_SEED=42`, `K_FOLDS=5` e `WINDOW_SIZE`.
  - [x] Subtask 1.3: Usar representacao tabular achatada das janelas.

- [x] Task 2: Criar nucleo compartilhado de k-fold (AC: #1-#4)
  - [x] Subtask 2.1: Criar `make_stratified_kfold()`.
  - [x] Subtask 2.2: Criar `run_sklearn_cross_validation()`.
  - [x] Subtask 2.3: Exportar JSON de metricas e CSV de predicoes por fold.

- [x] Task 3: Testar RF (AC: todos)
  - [x] Subtask 3.1: Testar cinco folds em dataset sintetico.
  - [x] Subtask 3.2: Validar persistencia de metricas e predicoes.

## Dev Notes

- `train_rf.py` nao serializa modelo real; isso pertence ao Epic 4.
- As metricas customizadas sao registradas por helper compartilhado, mantendo os scripts sem boilerplate repetitivo.
- O treino usa `n_jobs=-1` para viabilidade em CPU, mantendo `random_state=42`.

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-3.2]
- [Source: ml-pipeline/src/features/feature_engineer.py]
- [Source: _bmad-output/compartilhado/implementation-artifacts/3-1-setup-do-mlflow-e-infraestrutura-de-rastreamento.md]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `.venv/bin/python -m pytest tests/test_training_cross_validation.py -q` — passed in bateria agregada.

### Completion Notes List

- `train_rf.py` implementado com k-fold, seed fixo e MLflow.
- Metricas por fold e resumo media +/- desvio padrao exportados em `reports/metrics/random_forest_metrics.json`.
- Predicoes por fold exportadas para uso no relatorio por tipo de ataque.

### File List

- `ml-pipeline/src/training/train_rf.py`
- `ml-pipeline/src/training/cross_validation.py`
- `ml-pipeline/src/training/metrics.py`
- `ml-pipeline/src/training/data_preparation.py`
- `ml-pipeline/tests/test_training_cross_validation.py`
- `_bmad-output/compartilhado/implementation-artifacts/3-2-treino-e-avaliacao-do-random-forest-com-k-fold.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-25

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado.
- RF usa `config.RANDOM_SEED` e k-fold estratificado padronizado.
- As cinco metricas exigidas sao calculadas por fold e agregadas.
- Escopo de Epic 4 preservado.
