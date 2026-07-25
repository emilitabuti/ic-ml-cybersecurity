# Story 3.4: Treino e Avaliacao do LSTM/MLP com k-fold

Status: done

## Story

Como pesquisadora de ML (Emili),
Quero treinar o LSTM ou MLP como fallback com k-fold k=5 nas mesmas condicoes dos modelos anteriores,
Para que a comparacao temporal vs. tabular tenha suporte empirico solido.

## Acceptance Criteria

1. **Dado** que os dados sequenciais `(N, num_features)` estao prontos
   **Quando** executo `train_lstm.py`
   **Então** o script usa a representacao 3D para LSTM.

2. **Dado** que TensorFlow esta disponivel
   **Quando** o LSTM roda
   **Então** `tf.random.set_seed(config.RANDOM_SEED)` e `mlflow.tensorflow.autolog()` ficam ativos.

3. **Dado** que TensorFlow nao esta disponivel localmente
   **Quando** o fallback e permitido
   **Então** MLP e treinado como substituto explicito e `fallback_used=true` fica registrado.

4. **Dado** que todos os folds terminam
   **Quando** consulto os resultados
   **Então** F1, AUC-ROC, Precision, Recall e FPR aparecem como media +/- desvio padrao.

## Tasks / Subtasks

- [x] Task 1: Implementar `train_lstm.py` (AC: #1-#4)
  - [x] Subtask 1.1: Criar caminho TensorFlow/Keras LSTM sem import obrigatorio no modulo.
  - [x] Subtask 1.2: Aplicar `tf.random.set_seed(config.RANDOM_SEED)` no caminho LSTM.
  - [x] Subtask 1.3: Configurar `mlflow.tensorflow.autolog()` quando TensorFlow for aplicavel.

- [x] Task 2: Implementar fallback MLP explicito (AC: #3-#4)
  - [x] Subtask 2.1: Criar `build_mlp_fallback()`.
  - [x] Subtask 2.2: Registrar `fallback_reason` e `fallback_used=true`.
  - [x] Subtask 2.3: Documentar escolha Colab GPU T4 no README e nesta story.

- [x] Task 3: Testar (AC: #3-#4)
  - [x] Subtask 3.1: Testar fallback sem TensorFlow em dataset sintetico.

## Dev Notes

- Decisao documentada: LSTM completo deve ser executado preferencialmente no Google Colab com GPU T4. O ambiente local usa MLP fallback quando TensorFlow nao esta instalado.
- TensorFlow nao foi adicionado ao `requirements.txt` local para preservar instalacao leve e compatibilidade da suite em CPU/Python local; a alternativa Colab esta explicitamente documentada.
- A substituicao por MLP nunca e silenciosa: ha warning, mensagem no terminal e `fallback_used=true` no JSON.

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-3.4]
- [Source: _bmad-output/compartilhado/planning-artifacts/prd.md#Riscos-e-Mitigacoes]
- [Source: ml-pipeline/README.md#5-Executar-o-pipeline-de-treino]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `.venv/bin/python -m pytest tests/test_train_lstm.py -q` — passed in bateria agregada.

### Completion Notes List

- `train_lstm.py` implementado com caminho LSTM/TensorFlow e fallback MLP.
- `tf.random.set_seed` e `mlflow.tensorflow.autolog()` ficam no caminho TensorFlow.
- Fallback MLP documentado em story, README e arquivo de resultado.

### File List

- `ml-pipeline/src/training/train_lstm.py`
- `ml-pipeline/src/training/data_preparation.py`
- `ml-pipeline/tests/test_train_lstm.py`
- `ml-pipeline/README.md`
- `_bmad-output/compartilhado/implementation-artifacts/3-4-treino-e-avaliacao-do-lstm-mlp-com-k-fold.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-25

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado.
- Fallback MLP esta explicito e auditavel.
- LSTM preserva seed TensorFlow quando a dependencia existe.
- Nenhum artefato de modelo real foi serializado.
