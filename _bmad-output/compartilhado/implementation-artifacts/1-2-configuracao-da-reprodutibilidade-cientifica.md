# Story 1.2: Configuração da Reprodutibilidade Científica

Status: in-progress

## Story

Como pesquisadora de IC,
Quero um sistema com seed global fixo e dependências documentadas,
Para que qualquer experimento seja 100% reprodutível em qualquer máquina.

## Acceptance Criteria

1. **Dado** que o `ml-pipeline/` está scaffoldado  
   **Quando** abro `config.py`  
   **Então** `RANDOM_SEED = 42` está definido como constante  
   **E** `WINDOW_SIZE`, `CONFIDENCE_THRESHOLD` e `MODEL_PATH` estão definidos como variáveis configuráveis

2. **Dado** que o `ml-pipeline/` está scaffoldado  
   **Quando** abro `.env.example`  
   **Então** todas as variáveis de ambiente (`WINDOW_SIZE`, `CONFIDENCE_THRESHOLD`, `MODEL_PATH`) estão documentadas com valores padrão

3. **Dado** que o módulo `src/utils/seed.py` existe  
   **Quando** chamo `set_global_seed(RANDOM_SEED)`  
   **Então** o seed é aplicado em `random`, `numpy.random`, `os.environ["PYTHONHASHSEED"]`, e `torch`/`tensorflow` (se disponíveis)

4. **Dado** que dois experimentos são executados com os mesmos dados e `RANDOM_SEED = 42`  
   **Quando** comparo os resultados  
   **Então** as saídas são idênticas (variação ≤ 0.01%)

## Tasks / Subtasks

- [ ] Task 1: Verificar e completar `config.py` (AC: #1, #2)
  - [ ] Confirmar que `RANDOM_SEED = 42` existe como constante em `config.py`
  - [ ] Confirmar que `WINDOW_SIZE`, `CONFIDENCE_THRESHOLD`, `MODEL_PATH` existem em `config.py`
  - [ ] Confirmar que `.env.example` documenta todas as variáveis com valores padrão
  - [ ] Adicionar `PYTHONHASHSEED=42` ao `.env.example` (determinismo de hashing Python)

- [ ] Task 2: Criar módulo `src/utils/seed.py` com função `set_global_seed` (AC: #3, #4)
  - [ ] Criar pasta `ml-pipeline/src/utils/` com `__init__.py`
  - [ ] Criar `ml-pipeline/src/utils/seed.py` com função `set_global_seed(seed: int) -> None`
  - [ ] Aplicar seed em: `random.seed`, `numpy.random.seed`, `os.environ["PYTHONHASHSEED"]`
  - [ ] Aplicar seed em `tensorflow` via `tf.random.set_seed` (importação condicional — não falhar se ausente)
  - [ ] Logar o seed aplicado com `logging.getLogger(__name__).info(f"Global seed set to {seed}")`

- [ ] Task 3: Escrever testes de reprodutibilidade (AC: #1, #3, #4)
  - [ ] Criar `ml-pipeline/tests/test_reproducibility.py`
  - [ ] Teste: `test_config_random_seed_is_42` — importa `config.RANDOM_SEED` e verifica `== 42`
  - [ ] Teste: `test_config_variables_exist` — verifica `WINDOW_SIZE`, `CONFIDENCE_THRESHOLD`, `MODEL_PATH` existem e têm tipos corretos
  - [ ] Teste: `test_set_global_seed_returns_none` — chama `set_global_seed(42)` e verifica que não lança exceção
  - [ ] Teste: `test_numpy_reproducibility` — chama `set_global_seed(42)`, gera array aleatório, chama novamente, verifica arrays idênticos
  - [ ] Teste: `test_random_module_reproducibility` — mesmo padrão com `random.random()`
  - [ ] Teste: `test_sklearn_reproducibility` — usa `RandomState(RANDOM_SEED)` e verifica resultados idênticos em duas chamadas

- [ ] Task 4: Validar e fazer commit (AC: #4)
  - [ ] Executar `pytest tests/test_reproducibility.py -v` — todos os testes devem passar
  - [ ] Executar `pytest tests/` — sem regressões nos testes da story 1.1
  - [ ] Commit: `feat(story-1.2): reprodutibilidade científica — seed global e testes`

## Dev Notes

### Contexto Arquitetural Crítico

Esta story estabelece a **camada de reprodutibilidade científica** do projeto. O `RANDOM_SEED = 42` já foi criado na Story 1.1, mas a função `set_global_seed()` e os testes de garantia ainda não existem.

**Regra de ouro:** Todo módulo Python que usar aleatoriedade (treino, feature engineering, avaliação) deve chamar `set_global_seed(RANDOM_SEED)` no início. Esta função centraliza esse comportamento.

### Estado Atual (pós Story 1.1)

Já existe e está correto — **NÃO recriar**:
- `ml-pipeline/config.py` com `RANDOM_SEED = 42`, `WINDOW_SIZE`, `CONFIDENCE_THRESHOLD`, `MODEL_PATH`
- `ml-pipeline/.env.example` com `WINDOW_SIZE`, `CONFIDENCE_THRESHOLD`, `MODEL_PATH`

O que **falta criar**:
- `ml-pipeline/src/utils/__init__.py`
- `ml-pipeline/src/utils/seed.py`
- `ml-pipeline/tests/test_reproducibility.py`
- Adicionar `PYTHONHASHSEED=42` ao `.env.example`

### Implementação de `set_global_seed`

```python
# ml-pipeline/src/utils/seed.py
import logging
import os
import random

import numpy as np

logger = logging.getLogger(__name__)


def set_global_seed(seed: int) -> None:
    """Aplica seed global em todas as bibliotecas de aleatoriedade.

    Deve ser chamado no início de qualquer script de treino ou avaliação.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)

    try:
        import tensorflow as tf
        tf.random.set_seed(seed)
        logger.info("TensorFlow seed configurado: %d", seed)
    except ImportError:
        pass  # TensorFlow opcional neste ambiente

    logger.info("Global seed set to %d", seed)
```

### Padrão de Uso nos Módulos de Treino (documentar para futuros devs)

```python
# Exemplo de uso nos scripts de treino (Epic 3)
from config import RANDOM_SEED
from src.utils.seed import set_global_seed

set_global_seed(RANDOM_SEED)
# ... resto do código de treino
```

### Atenção: Não fazer nesta story

- ❌ Não implementar nenhuma lógica de treino ou ML — apenas infraestrutura de seed
- ❌ Não remover ou alterar a estrutura criada na Story 1.1
- ❌ Não instalar novas dependências (numpy, random, os já estão disponíveis)
- ❌ Não fazer `import tensorflow` diretamente no módulo — usar importação condicional (tensorflow não está instalado no ambiente atual)

### Estrutura de Pastas a Criar

```
ml-pipeline/
└── src/
    └── utils/
        ├── __init__.py    ← vazio (só registra como pacote Python)
        └── seed.py        ← função set_global_seed
```

### Testes Existentes (Story 1.1) — Não Quebrar

O arquivo `tests/test_scaffolding.py` tem 37 testes passando. A adição de `src/utils/` pode acionar testes de verificação de pastas — revisar se precisa adicionar `"src/utils"` à lista de `REQUIRED_DIRS` no `test_scaffolding.py`.

### Padrões de Código

- `snake_case` para todo código Python
- Logs com `logging.getLogger(__name__)` — **nunca `print()`**
- Importações condicionais para dependências opcionais (tensorflow)
- Docstrings em funções públicas

### References

- Configuração de reprodutibilidade: [Source: architecture.md#Cross-Cutting Concerns Identified]
- NFR de reprodutibilidade: [Source: architecture.md#Technical Constraints & Dependencies] — `variação ≤ 0.01% com mesmo seed`
- Story 1.1 (contexto): [Source: implementation-artifacts/1-1-inicializacao-do-monorepo-e-scaffolding-dos-projetos.md]
- config.py atual: [Source: ml-pipeline/config.py]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (claude-sonnet-4.6) via GitHub Copilot

### Debug Log References

### Completion Notes List

### File List
