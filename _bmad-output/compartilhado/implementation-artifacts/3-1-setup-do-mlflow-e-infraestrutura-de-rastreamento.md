# Story 3.1: Setup do MLflow e Infraestrutura de Rastreamento

Status: done

## Story

Como pesquisadora de ML (Emili),
Quero configurar o MLflow local com nomenclatura padronizada de experimentos,
Para que todos os runs de treino sejam automaticamente rastreados sem boilerplate adicional.

## Acceptance Criteria

1. **Dado** que o `ml-pipeline/` esta configurado
   **Quando** executo qualquer script de treino
   **Então** o MLflow cria automaticamente um experimento nomeado `ic-ml-cybersecurity-{model_type}`.

2. **Dado** que executo treino sklearn ou TensorFlow
   **Quando** o script inicializa
   **Então** `mlflow.sklearn.autolog()` ou `mlflow.tensorflow.autolog()` fica ativo.

3. **Dado** que os runs foram executados
   **Quando** executo `mlflow ui --backend-store-uri ./mlruns`
   **Então** os runs aparecem em `http://localhost:5000`.

4. **Dado** que o MLflow gera artefatos locais
   **Quando** verifico o repositorio
   **Então** `ml-pipeline/mlruns/` existe localmente e esta ignorado pelo Git.

## Tasks / Subtasks

- [x] Task 1: Implementar configuracao central do MLflow (AC: #1-#3)
  - [x] Subtask 1.1: Criar helper `setup_mlflow_tracking()`.
  - [x] Subtask 1.2: Padronizar nome de experimento `ic-ml-cybersecurity-{model_type}`.
  - [x] Subtask 1.3: Ativar autolog sklearn/tensorflow por flavor.

- [x] Task 2: Garantir armazenamento local e nao versionado (AC: #4)
  - [x] Subtask 2.1: Criar `ml-pipeline/mlruns/` local.
  - [x] Subtask 2.2: Confirmar `.gitignore` com `ml-pipeline/mlruns/`.

- [x] Task 3: Validar e documentar (AC: todos)
  - [x] Subtask 3.1: Testar setup MLflow com doubles sem carregar TensorFlow real.
  - [x] Subtask 3.2: Atualizar README com comando `mlflow ui`.

## Dev Notes

- MLflow ja estava fixado em `requirements.txt`.
- O helper fica em `src/training/mlflow_utils.py` para evitar repeticao nos scripts `train_*.py`.
- O diretorio `mlruns/` nao deve receber `.gitkeep`, pois esta explicitamente ignorado.

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-3.1]
- [Source: _bmad-output/compartilhado/planning-artifacts/architecture.md#ML-Pipeline-Patterns]
- [Source: ml-pipeline/.gitignore via .gitignore raiz]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `.venv/bin/python -m pytest tests/test_mlflow_tracking.py tests/test_training_metrics.py tests/test_training_cross_validation.py tests/test_train_lstm.py tests/test_evaluator.py -q` — 13 passed.

### Completion Notes List

- Criado `src/training/mlflow_utils.py` com tracking local, nome de experimento e autolog por flavor.
- Confirmado `ml-pipeline/mlruns/` local e ignorado pelo Git.
- README atualizado com execucao do MLflow UI em `http://localhost:5000`.

### File List

- `ml-pipeline/src/training/mlflow_utils.py`
- `ml-pipeline/tests/test_mlflow_tracking.py`
- `ml-pipeline/README.md`
- `ml-pipeline/.env.example`
- `_bmad-output/compartilhado/implementation-artifacts/3-1-setup-do-mlflow-e-infraestrutura-de-rastreamento.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-25

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado.
- Experimentos seguem a nomenclatura exigida.
- Autolog sklearn/tensorflow fica centralizado e testavel.
- `mlruns/` permanece fora do controle de versao.
