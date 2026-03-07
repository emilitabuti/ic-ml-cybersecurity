# Story 1.5: README de Reprodutibilidade

Status: done

## Story

Como pesquisador externo,
Quero instruções claras de instalação e execução do projeto,
Para que consiga reproduzir os experimentos principais em ≤ 30 minutos de setup.

## Acceptance Criteria

1. **Dado** que acesso o repositório pela primeira vez
   **Quando** sigo o README da raiz do projeto
   **Então** em ≤ 30 minutos consigo: clonar o repo, instalar dependências de `requirements.txt`, executar o pipeline de dados com o dataset disponível e ver as métricas no MLflow UI
   **E** o README documenta: pré-requisitos, estrutura do monorepo, instruções para `ml-pipeline/` e `dashboard/`, e como executar cada componente independentemente

2. **Dado** que o `ml-pipeline/README.md` já existe com instruções básicas
   **Quando** um pesquisador externo lê o arquivo
   **Então** encontra uma seção dedicada à reprodutibilidade científica com: pré-requisitos (Python 3.10+, pip, git), passos numerados de instalação, execução do pipeline de dados, execução e acesso ao MLflow UI e execução da suíte de testes
   **E** o tempo estimado de cada etapa principal está documentado

3. **Dado** que o `README.md` da raiz já existe como guia de colaboração da equipe
   **Quando** um pesquisador externo chega ao repositório
   **Então** a seção de reprodutibilidade científica na raiz direciona claramente para o `ml-pipeline/README.md` com o contexto científico do que está sendo reproduzido

## Tasks / Subtasks

- [x] Task 1: Atualizar `ml-pipeline/README.md` — seção Reprodutibilidade Científica (AC: #1, #2)
  - [x] Subtask 1.1: Adicionar/expandir seção "Reprodutibilidade Científica" com passos numerados e tempo estimado por etapa
  - [x] Subtask 1.2: Documentar instalação do MLflow e como acessar a UI (`http://127.0.0.1:5000`)
  - [x] Subtask 1.3: Documentar execução do pipeline de dados disponível (Story 1.3/1.4): `load_binary_dataset()` → `split_train_test()`
  - [x] Subtask 1.4: Adicionar seção "Pipeline de Treino" com estrutura de comandos futuros (placeholders para Epic 2/3) claramente marcados como `[a implementar]`
  - [x] Subtask 1.5: Documentar `pytest tests/ -v` como verificação de integridade do ambiente
  - [x] Subtask 1.6: Adicionar seção "O que NÃO está versionado" listando dados, modelos e `mlruns/`

- [x] Task 2: Atualizar `README.md` da raiz — adicionar seção Reprodução dos Experimentos (AC: #1, #3)
  - [x] Subtask 2.1: Adicionar item "10. Reprodução dos Experimentos" ao índice da raiz
  - [x] Subtask 2.2: Criar seção com contexto científico (dataset CICIDS2017, modelos RF/DT/LSTM, sliding window) e link para `ml-pipeline/README.md#reprodutibilidade-científica`
  - [x] Subtask 2.3: Incluir tempo estimado total de setup (≤ 30 min) e pré-requisitos mínimos

- [x] Task 3: Verificar consistência entre os READMEs (AC: #1–#3)
  - [x] Subtask 3.1: Garantir que os comandos documentados funcionam no estado atual do repositório
  - [x] Subtask 3.2: Verificar que os paths e nomes de módulos batem com a estrutura real de `ml-pipeline/`

## Dev Notes

### Estado atual (herdado das Stories 1.1–1.4)

```
ml-pipeline/
├── README.md                  ← EXISTS — tem instalação básica + API + reprodutibilidade simples
├── config.py                  ← RANDOM_SEED=42, TEST_SIZE=0.2, WINDOW_SIZE=10, CONFIDENCE_THRESHOLD=0.8, MODEL_PATH="models/"
├── requirements.txt           ← versões fixadas (scikit-learn==1.8.0, numpy==2.4.2, etc.)
├── .env.example               ← template de variáveis de ambiente
├── src/
│   ├── data/
│   │   ├── data_loader.py     ← load_binary_dataset(), load_dataset(), get_feature_names()
│   │   ├── data_validator.py  ← validate_binary_dataset(), DataValidationError
│   │   ├── data_splitter.py   ← split_train_test(X, y) — estratificado, seed=42
│   │   ├── schema/
│   │   │   └── features_schema.json  ← contrato v1.1.0 com split_contract
│   │   └── pipeline/
│   │       ├── collector.py
│   │       ├── cleaner.py
│   │       ├── scaler.py
│   │       └── preprocessor.py
│   └── utils/
│       └── seed.py            ← set_global_seed(seed=42)
└── tests/                     ← 91 testes passando (pytest)
    ├── test_data_loader.py
    ├── test_reproducibility.py
    ├── test_scaffolding.py
    └── test_data_splitter.py
```

**O que o `ml-pipeline/README.md` atual TEM:**
- Pré-requisitos (Python 3.10+, pip)
- Instalação (venv, pip install, .env)
- Estrutura de diretórios
- Execução da API (`uvicorn src.api.main:app --reload`)
- Seção "Reprodutibilidade" — apenas menção ao RANDOM_SEED e `pytest tests/`

**O que FALTA e precisa ser adicionado (gap identificado no epics.md):**
- Instruções do pipeline de treino completo (mesmo que parcial — o que existe hoje)
- Referência ao MLflow UI com comando de inicialização
- Tempo de setup do experimento end-to-end
- Passos para um pesquisador externo reproduzir os experimentos

### Conteúdo esperado da seção "Reprodutibilidade Científica"

A seção deve ter esta estrutura (tempo total ≤ 30 min):

```markdown
## Reprodutibilidade Científica

**Objetivo:** Pesquisador externo consegue reproduzir os experimentos em ≤ 30 minutos.

### Pré-requisitos (≈ 2 min de verificação)
- Python 3.10+
- pip atualizado (`pip install --upgrade pip`)
- Git
- ~500 MB de espaço em disco (sem dataset)
- ~3 GB adicionais para o dataset CICIDS2017

### 1. Clonar e instalar (≈ 5 min)
[comandos de clone, venv, pip install]

### 2. Verificar integridade do ambiente (≈ 2 min)
[pytest tests/ -v — deve passar 91 testes]

### 3. Preparar o dataset (≈ variável)
[instruções para obter CICIDS2017 e colocar em data/raw/]

### 4. Executar o pipeline de dados (≈ 10 min)
[comandos para coletar, limpar, escalar, dividir]

### 5. Iniciar MLflow e executar treino [a implementar — Epic 3]
[placeholder com estrutura esperada]

### 6. Ver métricas no MLflow UI
[mlflow ui — http://127.0.0.1:5000]

### O que NÃO está versionado
[data/, models/, mlruns/]
```

### MLflow — comandos essenciais para documentar

```bash
# Instalar (já em requirements.txt)
pip install mlflow

# Iniciar servidor de tracking local
mlflow ui
# Acesse: http://127.0.0.1:5000

# Ou apontar para pasta específica
mlflow ui --backend-store-uri ./mlruns
```

### Verificação dos comandos antes de documentar

Antes de finalizar o README, verifique que estes comandos funcionam no estado atual:

```bash
# 1. Instalação
cd ml-pipeline/
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Testes
python -m pytest tests/ -v
# Esperado: 91 testes passando (ou mais, se novos foram adicionados)

# 3. API (deve responder em /health)
uvicorn src.api.main:app --reload
curl http://127.0.0.1:8000/health

# 4. MLflow (deve abrir a UI)
mlflow ui
# Verificar http://127.0.0.1:5000
```

### Sobre os placeholders [a implementar]

Os scripts de treino (`src/training/train_rf.py`, `train_dt.py`, `train_lstm.py`) ainda não existem — são Épic 3. O README deve documentar a **estrutura esperada** desses comandos com marcação clara:

```markdown
> ⚠️ **Nota:** Os scripts de treino serão implementados no Epic 3. Os comandos abaixo mostram a estrutura esperada.

```bash
# [a implementar — Story 3.2]
python src/training/train_rf.py

# [a implementar — Story 3.3]
python src/training/train_dt.py

# [a implementar — Story 3.4]
python src/training/train_lstm.py
```

Quando implementados, os resultados estarão disponíveis no MLflow UI: http://127.0.0.1:5000
```

### Raiz `README.md` — seção a adicionar

A raiz já tem um README extenso focado em colaboração de equipe. A seção de reprodutibilidade deve ser **sucinta** e direcionar para `ml-pipeline/`:

```markdown
## 10. Reprodução dos Experimentos

Para reproduzir os experimentos científicos descritos no artigo:

**Setup estimado: ≤ 30 minutos**

O sistema aplica RF, DT e LSTM sobre janelas deslizantes do dataset CICIDS2017 para **previsão antecipada** de ataques. Os experimentos são rastreados com MLflow.

**Passos:**
1. Siga as instruções detalhadas em [`ml-pipeline/README.md`](ml-pipeline/README.md)
2. Use `RANDOM_SEED = 42` (definido em `config.py`) para reprodutibilidade exata
3. Resultados são visualizáveis em `http://127.0.0.1:5000` após `mlflow ui`

**Dataset:** [CICIDS2017](https://www.unb.ca/cic/datasets/ids-2017.html) — Canadian Institute for Cybersecurity (~2,8 GB, não versionado)
```

### O que NÃO fazer nesta story

- ❌ Não implementar scripts de treino (Epic 2/3)
- ❌ Não alterar `config.py` ou qualquer arquivo Python
- ❌ Não remover seções existentes do README da raiz — apenas adicionar
- ❌ Não inventar comandos que ainda não funcionam — marcar claramente como `[a implementar]`
- ❌ Não criar `REPRODUCIBILITY.md` separado — tudo dentro dos READMEs existentes

### Padrão de escrita

- Linguagem: Português (conforme todos os documentos do projeto)
- Tom: técnico e direto, sem jargões desnecessários
- Comandos: sempre em blocos de código com comentários explicativos
- Placeholders: sempre com marcação `[a implementar — Story X.Y]` e aviso visual `⚠️`

### References

- [Source: epics.md#Story-1.5] — User story, ACs e status parcial identificado
- [Source: documento-arquitetura-tecnica.md#15] — Seção 15 Reprodutibilidade Científica: seed, requirements.txt, README, MLflow
- [Source: documento-arquitetura-tecnica.md#17] — Seção 17 Estrutura do Repositório esperada com README.md na raiz e em ml-pipeline/
- [Source: ml-pipeline/README.md] — Estado atual do README — base para atualização
- [Source: README.md] — README da raiz — base para adição da seção de reprodutibilidade
- [Source: ml-pipeline/config.py] — RANDOM_SEED=42, TEST_SIZE=0.2, WINDOW_SIZE=10
- [Source: ml-pipeline/requirements.txt] — versões fixadas (scikit-learn 1.8.0, numpy 2.4.2, mlflow)
- [Source: sprint-status.yaml] — 1-5-readme-de-reprodutibilidade: backlog → ready-for-dev

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (claude-sonnet-4.6) via GitHub Copilot

### Debug Log References

- 94 testes passando com `.venv/bin/python -m pytest tests/ -q` (sem regressões)
- `mlflow 3.10.1` confirmado importável no venv do projeto
- `load_binary_dataset`, `split_train_test`, `config.RANDOM_SEED=42` confirmados funcionais
- Paths (`src/data/`, `src/training/`) conferidos contra estrutura real do repositório
- **Code review (2026-03-07):** URL de clone corrigida (`emili-tabuti` → `emilitabuti`), descrição de `data/processed/` desambiguada, instrução de execução do pipeline clarificada, contagem de testes atualizada para 94+, bloco gitignore ajustado para refletir entradas reais, seção 10 da raiz expandida com instruções básicas do dashboard

### Completion Notes List

- ✅ `ml-pipeline/README.md` — substituída seção "Reprodutibilidade" por seção expandida "Reprodutibilidade Científica" com 6 subsections: pré-requisitos, clonar/instalar, verificar ambiente, preparar dataset, pipeline de treino (placeholders `[a implementar]` para Epic 3), MLflow UI e "O que NÃO está versionado"
- ✅ `README.md` (raiz) — adicionado item 10 ao índice e seção "Reprodução dos Experimentos" com contexto científico, link para `ml-pipeline/README.md#reprodutibilidade-científica`, tempo ≤ 30 min e referência ao dataset CICIDS2017
- ✅ 94/94 testes passando — sem regressões
- ✅ Todos os comandos documentados verificados no estado atual do repositório
- ✅ **[Code Review Fix]** URL de clone corrigida: `emili-tabuti` → `emilitabuti` (H1)
- ✅ **[Code Review Fix]** `data/processed/` — descrição desambiguada na seção Estrutura (M3)
- ✅ **[Code Review Fix]** Passo 4 — instrução de execução via `python run_data_pipeline.py` adicionada (M2)
- ✅ **[Code Review Fix]** Seção 10 da raiz — instruções básicas do `dashboard/` adicionadas com marcação Epic 5 (M1)
- ✅ **[Code Review Fix]** Contagem de testes atualizada para `94+` (L1)
- ✅ **[Code Review Fix]** Bloco `gitignore` corrigido para refletir entradas reais do `.gitignore` (L2)

### File List

ml-pipeline/README.md
README.md
_bmad-output/compartilhado/implementation-artifacts/1-5-readme-de-reprodutibilidade.md
_bmad-output/compartilhado/implementation-artifacts/sprint-status.yaml
