# Story 1.3: Ingestão e Validação do Dataset CICIDS2017

Status: done

## Story

Como pesquisadora de ML (Emili),
Quero carregar e validar o dataset CSV do CICIDS2017 com verificação de schema formal,
Para que erros de formato ou dados inválidos sejam detectados antes do treinamento.

## Acceptance Criteria

1. **Dado** que existe um arquivo parquet válido em `data/processed/` com o contrato de Caroline  
   **Quando** chamo `load_binary_dataset(dataset="cic")`  
   **Então** o dataset é carregado com todas as features esperadas presentes  
   **E** retorna `(X, y)` como arrays numpy prontos para feature engineering

2. **Dado** que o arquivo parquet tem colunas incorretas ou `Binary_Label` ausente  
   **Quando** chamo `validate_binary_dataset(df)`  
   **Então** uma `DataValidationError` clara é lançada informando quais colunas estão ausentes  
   **E** o erro não é silenciado

3. **Dado** que o DataFrame contém valores NaN ou infinitos  
   **Quando** chamo `validate_binary_dataset(df)`  
   **Então** a exceção identifica qual coluna contém o valor inválido

4. **Dado** que o arquivo parquet não existe em `data/processed/`  
   **Quando** chamo `load_dataset()`  
   **Então** uma `FileNotFoundError` com instruções do pipeline de pré-processamento é lançada

## Tasks / Subtasks

- [x] Task 1: Criar `src/data/pipeline/` com scripts de pré-processamento de Caroline adaptados
  - [x] Adaptar `collect_cic_ids2017.py` → `pipeline/collector.py` (logging, docstrings, argparse)
  - [x] Adaptar `clean_dataset.py` → `pipeline/cleaner.py` (logging, type hints)
  - [x] Adaptar `scale_dataset.py` → `pipeline/scaler.py`
  - [x] Adaptar `make_model_ready.py` → `pipeline/preprocessor.py`

- [x] Task 2: Criar `src/data/data_loader.py` — ponto de entrada para consumir os dados
  - [x] `load_dataset(dataset, task)` — lê parquet de `data/processed/`
  - [x] `load_binary_dataset(dataset)` — retorna `(X, y)` para classificação binária
  - [x] `load_attacktype_dataset(dataset)` — retorna `(X, y)` para classificação multi-classe
  - [x] `get_feature_names(dataset, task)` — retorna lista de nomes das features
  - [x] Erros descritivos: `FileNotFoundError` com instruções do pipeline, `ValueError` para inputs inválidos

- [x] Task 3: Criar `src/data/data_validator.py` — validação estrutural dos DataFrames
  - [x] `validate_no_missing_values(df)` — detecta e reporta NaN por coluna
  - [x] `validate_no_infinite_values(df)` — detecta +inf e -inf
  - [x] `validate_binary_label(df)` — verifica presença e valores válidos (0 e 1)
  - [x] `validate_binary_dataset(df)` — validação completa do dataset binário
  - [x] `validate_attacktype_dataset(df)` — validação do dataset de tipo de ataque

- [x] Task 4: Criar `src/data/schema/features_schema.json` — contrato formal Caroline ↔ Emili
  - [x] Lista de attack types conhecidos do CIC-IDS2017
  - [x] Garantias estruturais do pré-processamento (sem NaN, sem inf, outliers preservados)
  - [x] Documentação de transformações aplicadas (log1p + RobustScaler, encoding)

- [x] Task 5: Copiar documentação técnica de Caroline para `docs/data-pipeline/`
  - [x] `00_source_selection.md`
  - [x] `01_data_collection.md`
  - [x] `02_data_cleaning.md`
  - [x] `03_feature_transformation.md`

- [x] Task 6: Escrever testes — `tests/test_data_loader.py` (AC: #1–#4)
  - [x] `TestValidateNoMissingValues` — 3 testes
  - [x] `TestValidateNoInfiniteValues` — 3 testes
  - [x] `TestValidateBinaryLabel` — 3 testes
  - [x] `TestValidateBinaryDataset` — 3 testes
  - [x] `TestValidateAttacktypeDataset` — 2 testes
  - [x] `TestDataLoaderFileNotFound` — 3 testes (erros claros)
  - [x] `TestLoadBinaryDataset` — 4 testes com dados sintéticos

- [x] Task 7: Validar e fazer commit
  - [x] Executar `pytest tests/test_data_loader.py -v` — 21/21 passando
  - [x] Executar `pytest tests/` — 72/72 sem regressões
  - [x] Commit: `feat(story-1.3): ingestão e validação do dataset CICIDS2017`

## Dev Notes

### Arquitetura da Camada de Dados

```
Caroline (upstream)          Emili (downstream)
─────────────────────        ──────────────────────────────────────
data/raw/cic_ids2017/    →   src/data/pipeline/collector.py
         ↓                   src/data/pipeline/cleaner.py
data/processed/              src/data/pipeline/scaler.py
  cic_ids2017_*              src/data/pipeline/preprocessor.py
  _model_ready_*.parquet  →  src/data/data_loader.py
                          →  src/data/data_validator.py
                             src/data/schema/features_schema.json
```

### Como Executar o Pipeline Completo (com dados reais)

```bash
cd ml-pipeline/
# Colocar dados brutos em data/raw/cic_ids2017/ (formato .parquet)
python -m src.data.pipeline.collector --dataset cic
python -m src.data.pipeline.cleaner --dataset cic
python -m src.data.pipeline.scaler --dataset cic
python -m src.data.pipeline.preprocessor --dataset cic
# Resultado: data/processed/cic_ids2017_model_ready_binary.parquet
```

### Uso nos Módulos de Treino (Epic 3)

```python
from src.data.data_loader import load_binary_dataset
from src.data.data_validator import validate_binary_dataset
from config import RANDOM_SEED
from src.utils.seed import set_global_seed

set_global_seed(RANDOM_SEED)
X, y = load_binary_dataset(dataset="cic")
# Pronto para feature engineering (Epic 2) ou treino (Epic 3)
```

### Padrões Seguidos

- `logging.getLogger(__name__)` — nunca `print()`
- Type hints em todas as funções públicas
- `DataValidationError` com mensagens descritivas (não silenciosas)
- Dados sintéticos nos testes — sem dependência de dados reais

### Atenção: Não fazer nesta story

- ❌ Não implementar feature engineering (Epic 2)
- ❌ Não executar train-test split (Story 1.4)
- ❌ Não modificar os scripts originais de Caroline

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (claude-sonnet-4.6) via GitHub Copilot

### Debug Log References

- `_PATHS["cic"]` é dict — monkeypatch requer `setitem` (não `setattr`)
- Fase RED: 5 testes falhando no monkeypatching
- Fase GREEN: 21/21 passando após correção
- Suite completa: 72/72 passando (21 novos + 51 anteriores)
- **Code review (2026-03-07):** SCHEMA_PATH tornado absoluto via `Path(__file__).parent`, `_PROCESSED_DIR` tornado absoluto, `get_feature_names` refatorado para ler schema parquet sem carregar dados, `RobustScaler` persistido com joblib, `inplace=True` removido do cleaner, 16 testes adicionados para pipeline scripts

### Completion Notes List

- ✅ `src/data/pipeline/collector.py` — adapta scripts de Caroline com logging e argparse
- ✅ `src/data/pipeline/cleaner.py` — limpeza CIC e UNSW com logging e type hints
- ✅ `src/data/pipeline/scaler.py` — log1p + RobustScaler com logging
- ✅ `src/data/pipeline/preprocessor.py` — datasets model-ready binário e multi-classe
- ✅ `src/data/data_loader.py` — carrega parquets model-ready, retorna (X, y) numpy
- ✅ `src/data/data_validator.py` — validações estruturais com `DataValidationError` descritiva
- ✅ `src/data/schema/features_schema.json` — contrato formal com attack types e garantias
- ✅ `docs/data-pipeline/` — 4 docs técnicos de Caroline integrados
- ✅ 21 novos testes em `tests/test_data_loader.py`
- ✅ 72/72 testes passando — sem regressões
- ✅ `.gitignore` atualizado: `src/data/` é código, não dados
- ✅ **[Code Review Fix]** `SCHEMA_PATH` tornado absoluto via `Path(__file__).parent` — elimina falha silenciosa quando CWD ≠ ml-pipeline/ (H1)
- ✅ **[Code Review Fix]** `_PROCESSED_DIR` tornado absoluto via `Path(__file__).parent.parent.parent` (H1)
- ✅ **[Code Review Fix]** `get_feature_names` refatorado para ler schema parquet com pyarrow sem carregar dataset completo (M2)
- ✅ **[Code Review Fix]** `scaler.py` persiste `RobustScaler` com joblib ao lado do parquet escalado (M1)
- ✅ **[Code Review Fix]** `inplace=True` removido de `cleaner.py` — pandas-compatible (M3)
- ✅ **[Code Review Fix]** `tests/test_pipeline.py` criado com 16 testes para cleaner.py (L1)
- ✅ **[Code Review Fix]** Schema anotado com `_todo_required_columns` (L2)
- ✅ 110/110 testes passando — sem regressões

### File List

ml-pipeline/src/data/pipeline/__init__.py
ml-pipeline/src/data/pipeline/collector.py
ml-pipeline/src/data/pipeline/cleaner.py
ml-pipeline/src/data/pipeline/scaler.py
ml-pipeline/src/data/pipeline/preprocessor.py
ml-pipeline/src/data/data_loader.py
ml-pipeline/src/data/data_validator.py
ml-pipeline/src/data/schema/features_schema.json
ml-pipeline/docs/data-pipeline/00_source_selection.md
ml-pipeline/docs/data-pipeline/01_data_collection.md
ml-pipeline/docs/data-pipeline/02_data_cleaning.md
ml-pipeline/docs/data-pipeline/03_feature_transformation.md
ml-pipeline/tests/test_data_loader.py
ml-pipeline/tests/test_pipeline.py
_bmad-output/compartilhado/implementation-artifacts/sprint-status.yaml
.gitignore
