# Story 4.1: Serializacao do Modelo Vencedor com Pipeline Completo

Status: done

## Story

Como pesquisadora de ML (Emili),
Quero serializar o modelo vencedor junto com todo o pipeline de pre-processamento,
Para que a inferencia funcione em qualquer ambiente limpo sem acesso ao codigo-fonte de treino.

## Acceptance Criteria

1. **Dado** que o modelo vencedor foi identificado
   **Quando** executo `model_serializer.py`
   **Então** o artefato exportado contem modelo, scaler, sliding window, features, encoder e metadados.

2. **Dado** que carrego o artefato em ambiente Python limpo
   **Quando** executo uma predicao de teste
   **Então** a inferencia funciona sem depender do codigo de treino.

3. **Dado** que o artefato esta incompleto
   **Quando** executo o carregamento ou inferencia
   **Então** uma excecao descritiva informa qual componente obrigatorio esta ausente.

## Tasks / Subtasks

- [x] Task 1: Implementar serializador portavel (AC: #1)
  - [x] Subtask 1.1: Selecionar vencedor a partir de `comparison_metrics.csv`.
  - [x] Subtask 1.2: Persistir artefato joblib com modelo, scaler, window transformer, `feature_names`, `label_encoding` e metadados.
  - [x] Subtask 1.3: Suportar modelos sklearn e LSTM/Keras por bytes.

- [x] Task 2: Implementar carregamento e inferencia pelo artefato (AC: #2, #3)
  - [x] Subtask 2.1: Validar componentes obrigatorios em `load_serialized_model()`.
  - [x] Subtask 2.2: Aplicar scaler e sliding window no `predict_from_artifact()`.
  - [x] Subtask 2.3: Decodificar labels e calcular confianca.

- [x] Task 3: Gerar artefatos reais e validar (AC: #1-#3)
  - [x] Subtask 3.1: Gerar `ml-pipeline/models/model_rf.pkl`.
  - [x] Subtask 3.2: Gerar `ml-pipeline/models/model_lstm.pkl`.
  - [x] Subtask 3.3: Persistir scalers em `data/processed/*_scaled.joblib`.
  - [x] Subtask 3.4: Cobrir serializacao, portabilidade e falhas em testes.

## Dev Notes

- O artefato e um `dict` joblib com tipos portaveis.
- RF/DT usam janelas achatadas; LSTM usa janelas sequenciais.
- O contrato de label padrao mapeia `0 -> BENIGN` e `1 -> Attack`.
- Arquivos de modelo e dados processados continuam ignorados pelo Git por tamanho.

### References

- [Source: _bmad-output/compartilhado/planning-artifacts/epics.md#Story-4.1]
- [Source: ml-pipeline/src/models/model_serializer.py]
- [Source: ml-pipeline/tests/test_model_serializer.py]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `.venv/bin/python -m pytest tests/test_model_serializer.py -q` — validado durante a implementacao da story.
- `.venv/bin/python -m pytest -q` — regressao atual: `159 passed, 4 warnings`.
- Carga local dos artefatos:
  - `models/model_rf.pkl random_forest 10 206 1.897s`
  - `models/model_lstm.pkl lstm 10 77 0.011s`

### Completion Notes List

- Implementado `src/models/model_serializer.py`.
- Gerado `model_rf.pkl` com pipeline completo e inferencia validada.
- Gerado `model_lstm.pkl` com caminho Keras/LSTM validado em ambiente TensorFlow.
- Scalers persistidos para CIC e UNSW.
- Testes cobrem serializacao, carregamento em ambiente isolado, inferencia e erro descritivo para artefato incompleto.

### File List

- `ml-pipeline/src/models/model_serializer.py`
- `ml-pipeline/tests/test_model_serializer.py`
- `ml-pipeline/models/model_rf.pkl`
- `ml-pipeline/models/model_lstm.pkl`
- `ml-pipeline/data/processed/cic_ids2017_scaled.joblib`
- `ml-pipeline/data/processed/unsw_nb15_scaled.joblib`
- `_bmad-output/compartilhado/implementation-artifacts/4-1-serializacao-do-modelo-vencedor-com-pipeline-completo.md`

## Senior Developer Review (AI)

Reviewer: GPT-5 Codex on 2026-07-29

Outcome: Approve

Findings:

- Nenhum bloqueador encontrado.
- Artefato RF carrega abaixo do limite de 5s.
- Testes de portabilidade e validacao de componentes obrigatorios cobrem os riscos principais da story.
