# Story 1.4: Divisão Train/Test Estratificada e Formalização do Contrato de Dados

Status: ready-for-dev

## Story

Como pesquisadora de ML (Emili),
Quero dividir os dados em treino e teste antes de qualquer transformação e formalizar o contrato de dados no schema,
Para que não haja data leakage e o contrato de dados esteja completamente documentado.

## Acceptance Criteria

1. **Dado** que o dataset foi carregado e validado (Story 1.3)
   **Quando** chamo `split_train_test(X, y)`
   **Então** o split ocorre estratificado por label com `random_state=config.RANDOM_SEED`
   **E** nenhuma transformação (normalização, feature selection, sliding window) foi aplicada antes do split
   **E** a proporção do split respeita o valor configurável `TEST_SIZE` (padrão `0.2`)

2. **Dado** que executo o split com o mesmo seed em duas execuções independentes
   **Quando** verifico os índices do conjunto de teste
   **Então** os conjuntos `X_train`, `X_test`, `y_train`, `y_test` são idênticos nas duas execuções

3. **Dado** que o split é executado
   **Quando** verifico a distribuição de classes em treino e teste
   **Então** a proporção de labels (0=benigno, 1=ataque) é preservada em ambos os conjuntos (estratificação válida)

4. **Dado** que o arquivo `src/data/schema/features_schema.json` existe (criado na Story 1.3)
   **Quando** a Story 1.4 é concluída
   **Então** o schema é atualizado com a seção `"split_contract"` documentando: proporção treino/teste, estratificação por label, seed usado e política de leakage prevention

## Tasks / Subtasks

- [ ] Task 1: Criar `src/data/data_splitter.py` — módulo de divisão train/test (AC: #1, #2, #3)
  - [ ] Subtask 1.1: Implementar `split_train_test(X, y, test_size=None, random_state=None) -> tuple` que retorna `(X_train, X_test, y_train, y_test)`
  - [ ] Subtask 1.2: `test_size` padrão lido de `config.TEST_SIZE` (novo campo em `config.py`, default `0.2`)
  - [ ] Subtask 1.3: `random_state` padrão lido de `config.RANDOM_SEED`
  - [ ] Subtask 1.4: Usar `sklearn.model_selection.train_test_split` com `stratify=y`
  - [ ] Subtask 1.5: Log descritivo: tamanho dos conjuntos, proporção de classes, seed usado
  - [ ] Subtask 1.6: Type hints completos e docstring com exemplo de uso

- [ ] Task 2: Adicionar `TEST_SIZE` ao `config.py` (AC: #1)
  - [ ] Subtask 2.1: `TEST_SIZE: float = float(os.getenv("TEST_SIZE", "0.2"))` — configurável via env var

- [ ] Task 3: Atualizar `src/data/schema/features_schema.json` com seção `split_contract` (AC: #4)
  - [ ] Subtask 3.1: Adicionar campo `"split_contract"` com: `test_size`, `stratify_by`, `random_state_source`, `leakage_prevention_policy`, `split_applied_before`
  - [ ] Subtask 3.2: Adicionar campo `"version"` ao schema para rastrear evolução (`"1.1.0"`)

- [ ] Task 4: Escrever testes — `tests/test_data_splitter.py` (AC: #1–#4)
  - [ ] Subtask 4.1: `TestSplitTrainTestBasic` — split retorna 4 arrays, tamanhos corretos (80/20)
  - [ ] Subtask 4.2: `TestSplitReproducibility` — dois splits com mesmo seed produzem índices idênticos
  - [ ] Subtask 4.3: `TestSplitStratification` — proporção de classes preservada em treino e teste (tolerância ±2%)
  - [ ] Subtask 4.4: `TestSplitCustomParams` — `test_size` e `random_state` customizáveis via parâmetro
  - [ ] Subtask 4.5: `TestSplitNoLeakage` — índices de treino e teste são disjuntos (sem sobreposição)
  - [ ] Subtask 4.6: `TestConfigTestSize` — `config.TEST_SIZE` existe, é float, entre 0.1 e 0.5

- [ ] Task 5: Rodar suite completa e fazer commit (AC: todos)
  - [ ] Subtask 5.1: `pytest tests/test_data_splitter.py -v` — todos os novos testes passando
  - [ ] Subtask 5.2: `pytest tests/` — sem regressões na suite completa
  - [ ] Subtask 5.3: Commit: `feat(story-1.4): split train/test estratificado e contrato de dados`

## Dev Notes

### Contexto Essencial — O que já existe (Story 1.3)

```
ml-pipeline/
├── config.py                          # RANDOM_SEED=42, WINDOW_SIZE, CONFIDENCE_THRESHOLD
├── src/
│   └── data/
│       ├── __init__.py
│       ├── data_loader.py             # load_binary_dataset(), load_dataset(), get_feature_names()
│       ├── data_validator.py          # validate_binary_dataset(), DataValidationError
│       ├── schema/
│       │   └── features_schema.json   # Contrato Caroline↔Emili — ATUALIZAR nesta story
│       └── pipeline/
│           ├── collector.py
│           ├── cleaner.py
│           ├── scaler.py
│           └── preprocessor.py
└── tests/
    ├── test_data_loader.py            # 21 testes — NÃO QUEBRAR
    ├── test_reproducibility.py        # testes de seed — NÃO QUEBRAR
    └── test_scaffolding.py            # testes de scaffolding — NÃO QUEBRAR
```

### Implementação do `data_splitter.py` — Esqueleto

```python
"""Módulo de divisão train/test estratificada para o pipeline de ML.

Garante que o split ocorra ANTES de qualquer transformação
(feature selection, sliding window, normalização adicional),
prevenindo data leakage entre treino e teste.

Uso típico:
    from src.data.data_loader import load_binary_dataset
    from src.data.data_splitter import split_train_test
    from config import RANDOM_SEED

    X, y = load_binary_dataset(dataset="cic")
    X_train, X_test, y_train, y_test = split_train_test(X, y)
"""
import logging
from typing import Optional, Tuple

import numpy as np
from sklearn.model_selection import train_test_split

import config

logger = logging.getLogger(__name__)


def split_train_test(
    X: np.ndarray,
    y: np.ndarray,
    test_size: Optional[float] = None,
    random_state: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Divide dados em conjuntos de treino e teste com estratificação.

    IMPORTANTE: Esta função deve ser chamada ANTES de qualquer transformação
    (feature selection, sliding window, normalização). Chamá-la depois
    constitui data leakage.

    Args:
        X: Array de features, shape (n_samples, n_features).
        y: Array de labels, shape (n_samples,).
        test_size: Proporção do teste. Default: config.TEST_SIZE (0.2).
        random_state: Seed. Default: config.RANDOM_SEED (42).

    Returns:
        Tupla (X_train, X_test, y_train, y_test).
    """
    _test_size = test_size if test_size is not None else config.TEST_SIZE
    _random_state = random_state if random_state is not None else config.RANDOM_SEED

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=_test_size,
        random_state=_random_state,
        stratify=y,
    )

    # Log descritivo
    logger.info(
        "Split train/test: total=%d | train=%d (%.0f%%) | test=%d (%.0f%%) | seed=%d",
        len(y), len(y_train), 100 * (1 - _test_size),
        len(y_test), 100 * _test_size, _random_state,
    )
    # Proporção de classes
    train_attack_ratio = y_train.mean()
    test_attack_ratio = y_test.mean()
    logger.info(
        "Proporção de ataques: train=%.2f%% | test=%.2f%%",
        100 * train_attack_ratio, 100 * test_attack_ratio,
    )

    return X_train, X_test, y_train, y_test
```

### Atualização do `features_schema.json`

Adicionar ao JSON existente (não substituir — apenas adicionar campos):

```json
{
  "_version": "1.1.0",
  "split_contract": {
    "test_size": 0.2,
    "stratify_by": "Binary_Label",
    "random_state_source": "config.RANDOM_SEED (default: 42)",
    "leakage_prevention_policy": "split_first",
    "split_applied_before": ["feature_selection", "sliding_window", "additional_scaling"],
    "description": "O split train/test deve ser aplicado ANTES de qualquer transformação de features para prevenir data leakage."
  }
}
```

### `config.py` — Adição necessária

```python
TEST_SIZE: float = float(os.getenv("TEST_SIZE", "0.2"))
```

### Padrões obrigatórios (herdados da Story 1.3)

- `logging.getLogger(__name__)` — **NUNCA** `print()`
- Type hints em todas as funções públicas
- Dados sintéticos nos testes — sem dependência de `data/processed/`
- Mensagens de erro descritivas (não silenciosas)

### Padrão de testes com dados sintéticos

```python
import numpy as np
import pytest

@pytest.fixture
def synthetic_binary_data():
    """Dataset sintético com distribuição 70% benigno / 30% ataque."""
    rng = np.random.default_rng(seed=0)
    n = 1000
    X = rng.random((n, 10))
    y = rng.integers(0, 2, n)
    # Garante que há ambas as classes
    y[:700] = 0
    y[700:] = 1
    return X, y
```

### O que NÃO fazer nesta story

- ❌ Não implementar feature selection (Story 2.1)
- ❌ Não implementar sliding window (Story 2.2)
- ❌ Não modificar `data_loader.py` ou `data_validator.py`
- ❌ Não substituir `features_schema.json` — apenas adicionar campos
- ❌ Não usar `print()` — sempre `logging`

### Fluxo de uso esperado (Epic 2+)

```
load_binary_dataset()          ← Story 1.3 ✅
       ↓
split_train_test(X, y)         ← Story 1.4 (esta story)
       ↓
feature_selector.fit(X_train)  ← Story 2.1
feature_selector.transform(X_train), feature_selector.transform(X_test)
       ↓
sliding_window(X_train_selected), sliding_window(X_test_selected)  ← Story 2.2
```

### References

- [Source: epics.md#Story-1.4] — User story, ACs e status
- [Source: architecture.md#Data-Science-&-ML] — Leakage prevention como princípio #1, `sklearn.model_selection`
- [Source: config.py] — `RANDOM_SEED=42`, estrutura de env vars
- [Source: src/data/data_loader.py] — Padrões de logging e type hints
- [Source: tests/test_reproducibility.py] — Padrão de testes de seed
- [Source: src/data/schema/features_schema.json] — Schema existente v1.0.0 a ser atualizado
- [Source: requirements.txt] — `scikit-learn==1.8.0`, `numpy==2.4.2`

## Dev Agent Record

### Agent Model Used

_a preencher pelo agente de desenvolvimento_

### Debug Log References

### Completion Notes List

### File List
