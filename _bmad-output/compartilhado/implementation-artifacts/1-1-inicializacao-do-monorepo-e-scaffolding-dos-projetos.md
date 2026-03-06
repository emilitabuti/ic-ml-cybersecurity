# Story 1.1: Inicialização do Monorepo e Scaffolding dos Projetos

Status: ready-for-dev

## Story

Como pesquisadora de IC,
Quero inicializar o repositório monorepo com os dois projetos scaffoldados (ML Pipeline e Dashboard React),
Para que toda a equipe parta de uma base estruturada, padronizada e pronta para desenvolvimento.

## Acceptance Criteria

1. **Dado** que estou na raiz do projeto  
   **Quando** executo os comandos de inicialização descritos no README  
   **Então** o diretório `ml-pipeline/` existe com estrutura Cookiecutter Data Science + `src/api/` adicionado manualmente

2. **E** o diretório `dashboard/` existe com Vite + React + TypeScript + Tailwind CSS + shadcn/ui + Recharts instalados

3. **E** `ml-pipeline/requirements.txt` lista todas as dependências com versões fixadas (via `pip freeze`)

4. **E** `dashboard/package.json` lista todas as dependências com versões fixadas

5. **E** ambos os projetos iniciam sem erros (`uvicorn src/api/main:app` e `npm run dev`)

## Tasks / Subtasks

- [ ] Task 1: Scaffolding do ML Pipeline (AC: #1, #3)
  - [ ] Instalar cookiecutter: `pip install cookiecutter`
  - [ ] Executar: `cookiecutter https://github.com/drivendataorg/cookiecutter-data-science`
  - [ ] Criar manualmente `ml-pipeline/src/api/` com `__init__.py` e `main.py` mínimo (FastAPI app vazio)
  - [ ] Criar estrutura de pastas conforme arquitetura: `src/data/`, `src/features/`, `src/training/`, `src/models/`, `src/api/routes/`, `src/api/schemas/`, `src/api/services/`
  - [ ] Adicionar `__init__.py` em cada subpacote Python
  - [ ] Instalar dependências: `pip install fastapi uvicorn mlflow scikit-learn tensorflow pandas numpy pydantic pandera joblib`
  - [ ] Gerar `requirements.txt`: `pip freeze > requirements.txt`
  - [ ] Criar `ml-pipeline/config.py` com `RANDOM_SEED = 42`, `WINDOW_SIZE`, `CONFIDENCE_THRESHOLD`, `MODEL_PATH`
  - [ ] Criar `ml-pipeline/.env.example` com todas as variáveis de ambiente documentadas
  - [ ] Criar pastas de dados: `data/raw/`, `data/processed/`, `data/schema/`, `models/`, `notebooks/`, `mlruns/`
  - [ ] Criar `tests/` com `__init__.py`

- [ ] Task 2: Scaffolding do Dashboard React (AC: #2, #4)
  - [ ] Executar: `npm create vite@latest dashboard -- --template react-ts`
  - [ ] Instalar dependências: `cd dashboard && npm install`
  - [ ] Configurar Tailwind: `npx tailwindcss init -p` + atualizar `tailwind.config.js` e `index.css`
  - [ ] Inicializar shadcn/ui: `npx shadcn@latest init` (tema: dark, style: default, base color: slate)
  - [ ] Instalar Recharts: `npm install recharts`
  - [ ] Instalar TanStack Query: `npm install @tanstack/react-query`
  - [ ] Criar estrutura de pastas: `src/components/`, `src/pages/`, `src/hooks/`, `src/services/`
  - [ ] Criar `src/services/api.ts` (arquivo vazio com comentário: único ponto de acesso à FastAPI)
  - [ ] Criar `src/config.ts` com `POLLING_INTERVAL_MS` e `API_BASE_URL`
  - [ ] Criar `dashboard/.env.example` com `VITE_API_URL=http://127.0.0.1:8000`
  - [ ] Envolver App em `QueryClientProvider` no `main.tsx`

- [ ] Task 3: Validação e Versionamento (AC: #5)
  - [ ] Verificar que `uvicorn src.api.main:app --reload` inicia sem erros no `ml-pipeline/`
  - [ ] Verificar que `npm run dev` inicia sem erros no `dashboard/`
  - [ ] Criar `.gitignore` raiz cobrindo: `__pycache__/`, `*.pyc`, `.env`, `data/raw/`, `mlruns/`, `models/*.pkl`, `models/*.h5`, `node_modules/`, `dist/`
  - [ ] Commit inicial: `feat(epic1): scaffolding monorepo ml-pipeline e dashboard`

## Dev Notes

### Contexto Arquitetural Crítico

Esta é a **Story 1.1 — fundação de todo o projeto**. Não há código anterior. O dev deve criar do zero a estrutura completa do monorepo conforme especificado na arquitetura.

**Sistema bi-componente:**
- `ml-pipeline/` → Python (treino, avaliação, FastAPI serving)
- `dashboard/` → React (interface de monitoramento e alertas)

**Regra crítica de isolamento:** Cada componente tem suas próprias dependências, README e ciclo de vida independente. Não misturar configs de um no outro.

### Versões de Dependências (fixar estas)

**Python (`ml-pipeline/requirements.txt`):**
```
fastapi==0.111.x
uvicorn==0.29.x
mlflow==2.x
scikit-learn==1.4.x
tensorflow==2.16.x
pandas==2.2.x
numpy==1.26.x
pydantic==2.x
pandera==0.20.x
joblib==1.3.x
python-dotenv==1.0.x
```

**Node (`dashboard/package.json` — além do Vite/React/TypeScript):**
```
tailwindcss: ^3.4.x
@radix-ui/react-* (via shadcn)
recharts: ^2.12.x
@tanstack/react-query: ^5.x
```

### Estrutura Completa de Pastas a Criar

```
ic-ml-cybersecurity/
├── README.md                          ← atualizar com estrutura do monorepo
├── .gitignore
│
├── ml-pipeline/
│   ├── README.md
│   ├── requirements.txt
│   ├── config.py                      ← RANDOM_SEED=42, WINDOW_SIZE, CONFIDENCE_THRESHOLD, MODEL_PATH
│   ├── .env.example
│   ├── data/
│   │   ├── raw/                       ← vazio (gitignored)
│   │   ├── processed/                 ← vazio (gitignored)
│   │   └── schema/                    ← features_schema.json virá na Story 1.4
│   ├── models/                        ← vazio (gitignored)
│   ├── notebooks/
│   │   └── 01_eda.ipynb               ← placeholder vazio
│   ├── src/
│   │   ├── data/
│   │   │   └── __init__.py
│   │   ├── features/
│   │   │   └── __init__.py
│   │   ├── training/
│   │   │   └── __init__.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── main.py                ← FastAPI app mínimo (health check)
│   │       ├── routes/
│   │       │   └── __init__.py
│   │       ├── schemas/
│   │       │   └── __init__.py
│   │       └── services/
│   │           └── __init__.py
│   ├── tests/
│   │   └── __init__.py
│   └── mlruns/                        ← vazio (gitignored)
│
└── dashboard/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tailwind.config.js
    ├── .env.example                   ← VITE_API_URL=http://127.0.0.1:8000
    └── src/
        ├── main.tsx                   ← com QueryClientProvider
        ├── App.tsx
        ├── config.ts                  ← POLLING_INTERVAL_MS=5000, API_BASE_URL
        ├── components/                ← vazio
        ├── pages/                     ← vazio
        ├── hooks/                     ← vazio
        └── services/
            └── api.ts                 ← esqueleto vazio (ponto único de acesso à API)
```

### FastAPI main.py mínimo (ponto de partida)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="IC ML Cybersecurity API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}
```

### config.py mínimo

```python
import os
from dotenv import load_dotenv

load_dotenv()

RANDOM_SEED: int = 42
WINDOW_SIZE: int = int(os.getenv("WINDOW_SIZE", "10"))
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
MODEL_PATH: str = os.getenv("MODEL_PATH", "models/")
```

### Padrões de Código (obrigatório seguir)

- `snake_case` para todo código Python (arquivos, funções, variáveis)
- `PascalCase` apenas para componentes React e classes Python
- Toda configuração Python centralizada em `config.py` — **nunca magic strings espalhadas**
- `src/services/api.ts` é o **único ponto de acesso** à FastAPI no frontend — sem `fetch` direto em componentes
- Nunca usar `print()` em produção Python — usar `logging.getLogger(__name__)`

### .gitignore Raiz (conteúdo mínimo)

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.env
ml-pipeline/data/raw/
ml-pipeline/mlruns/
ml-pipeline/models/*.pkl
ml-pipeline/models/*.h5

# Node
node_modules/
dist/
dashboard/.env

# OS
.DS_Store
```

### Project Structure Notes

- A estrutura do `ml-pipeline/` segue Cookiecutter Data Science, mas com adição manual de `src/api/`
- O `dashboard/` usa o template padrão do Vite React TypeScript, estendido com Tailwind + shadcn + Recharts
- Ambos os projetos são independentes — não há pasta compartilhada entre eles nesta story
- O contrato de dados (`features_schema.json`) é criado na **Story 1.4**, não aqui

### Atenção: Não fazer nesta story

- ❌ Não implementar lógica de ML (treino, predição) — apenas estrutura
- ❌ Não implementar endpoints além de `/health` — isso é Epic 4
- ❌ Não criar componentes React reais — apenas estrutura de pastas e esqueletos
- ❌ Não processar ou carregar dados — isso é Story 1.3

### References

- Estrutura completa do projeto: [Source: architecture.md#Project Structure & Boundaries]
- Starter A (Dashboard): [Source: architecture.md#Componente A — Dashboard (Frontend React)]
- Starter B (ML Pipeline): [Source: architecture.md#Componente B — ML Pipeline (Backend Python)]
- Padrões de código: [Source: architecture.md#Code Standards & Conventions]
- CORS e API: [Source: architecture.md#API Boundary (FastAPI ↔ React)]
- Reprodutibilidade: [Source: epics.md#Story 1.2] (implementada na próxima story)

## Dev Agent Record

### Agent Model Used

_a preencher pelo agente dev_

### Debug Log References

### Completion Notes List

### File List
