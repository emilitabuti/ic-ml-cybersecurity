---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
workflowStatus: 'complete'
completedAt: '2026-02-21'
lastStatusUpdate: '2026-03-06'
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
  - "_bmad-output/planning-artifacts/ux-design-specification.md"
implementationStatus:
  epic1: "done"
  epic2: "not_started"
  epic3: "not_started"
  epic4: "not_started"
  epic5: "scaffolding_only"
---

# ic-ml-cybersecurity - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for ic-ml-cybersecurity, decomposing the requirements from the PRD, UX Design and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: O sistema aceita como entrada um dataset CSV com features do CICIDS2017 normalizadas
FR2: O sistema valida o formato do CSV de entrada (colunas esperadas, ausência de valores nulos)
FR3: O sistema divide os dados em conjuntos de treino e teste antes de qualquer transformação
FR4: Emili pode executar feature selection sobre o conjunto de treino, selecionando as top-N features por importância (RF) ou correlação com o label, onde N e o threshold mínimo são configuráveis antes da execução
FR5: O sistema transforma sequências de registros de tráfego em janelas deslizantes de tamanho configurável (sliding window)
FR6: O sistema aplica sliding window separadamente sobre treino e teste — sem vazamento de dados entre os conjuntos
FR7: Emili pode configurar o tamanho N da janela deslizante (valores a testar: N=5, N=10, N=20)
FR8: Emili pode treinar um modelo Random Forest sobre os dados de treino
FR9: Emili pode treinar um modelo Decision Tree sobre os dados de treino
FR10: Emili pode treinar um modelo LSTM ou MLP sobre os dados de treino
FR11: O sistema avalia cada modelo com k-fold cross-validation com k configurável (padrão k=5)
FR12: O sistema calcula F1-Score, AUC-ROC, Precision, Recall e FPR para cada modelo
FR13: O sistema reporta métricas com média e desvio padrão entre os folds do k-fold
FR14: O sistema produz tabela comparativa de métricas para todos os modelos avaliados
FR15: Emili pode configurar hiperparâmetros de cada modelo antes do treino
FR16: O sistema registra automaticamente parâmetros de cada run (algoritmo, hiperparâmetros, tamanho da janela)
FR17: O sistema registra automaticamente as métricas de avaliação de cada run
FR18: Emili pode comparar resultados de múltiplos runs em painel de rastreamento de experimentos com visualização lado a lado de métricas e parâmetros
FR19: Emili pode exportar resultados dos experimentos em formato CSV para o artigo
FR20: O sistema serializa o modelo treinado em formato compatível com inferência, incluindo todo o pipeline de pré-processamento necessário, sem dependência do código-fonte de treino
FR21: Emili pode selecionar e exportar o modelo vencedor para uso em produção
FR22: O artefato exportado inclui todo o pipeline de pré-processamento necessário para inferência (scaler, window transformer, encoder)
FR23: O sistema expõe endpoint HTTP `POST /predict` para receber janela de tráfego e retornar predição
FR24: O endpoint retorna: tipo de ameaça prevista, nível de confiança do modelo e identificador do modelo
FR25: O sistema disponibiliza documentação interativa do endpoint (`GET /docs`)
FR26: O sistema disponibiliza endpoint mock com respostas fixas para desenvolvimento paralelo da interface de Isabela
FR27: O sistema de alertas exibe tipo de ameaça prevista, nível de confiança do modelo, timestamp da janela de tráfego e identificador do modelo que gerou a predição
FR28: O sistema de alertas mantém histórico das últimas ≥ 100 notificações com tipo de ameaça, confiança, timestamp e status (confirmado / descartado pelo analista)
FR29: Analistas podem configurar threshold mínimo de confiança para disparo de alertas e registrar feedback por alerta (confirmar ameaça real ou descartar como falso positivo)
FR30: O sistema garante resultados reprodutíveis com seed configurável fixo em todos os modelos, produzindo métricas idênticas para a mesma combinação de dados e hiperparâmetros
FR31: O projeto documenta todas as dependências com versões fixadas em arquivo de dependências padrão do ecossistema, garantindo ambiente reprodutível
FR32: O projeto fornece instruções de instalação e execução para reprodução dos experimentos (README)
FR33: O sistema gera relatório de desempenho dos modelos exportável para inclusão no artigo científico

### NonFunctional Requirements

NFR1: A inferência do modelo via `POST /predict` deve retornar resposta em ≤ 10 segundos para uma janela de tráfego de tamanho N ≤ 20 registros
NFR2: O carregamento do modelo serializado na inicialização da API deve completar em ≤ 5 segundos
NFR3: O treino de RF e DT sobre o CICIDS2017 completo deve completar em ≤ 2 horas em CPU (Intel Core i5 ou equivalente, 8GB RAM)
NFR4: O treino do LSTM deve ser viável em ≤ 4 horas no Google Colab (GPU T4 gratuita)
NFR5: Executando o pipeline com os mesmos dados e seed configurável fixo, os resultados das métricas devem ser idênticos em qualquer execução (variação ≤ 0.01%)
NFR6: O ambiente de execução deve ser reconstituível via gerenciador de pacotes padrão a partir do arquivo de dependências, em Python ≥ 3.10, sem conflitos de dependências
NFR7: O README deve permitir que um pesquisador externo reproduza os experimentos principais em ≤ 30 minutos de setup
NFR8: O endpoint `POST /predict` deve aceitar e retornar JSON válido conforme schema documentado em `/docs`
NFR9: O pipeline de treino deve aceitar qualquer CSV que respeite o contrato de interface definido com Caroline sem modificação de código
NFR10: O modelo exportado deve ser carregável e utilizável para inferência em ambiente limpo sem acesso ao código-fonte de treino, verificável ao executar predição com sucesso em ambiente de instalação nova contendo apenas o artefato exportado e o arquivo de dependências
NFR11: A API deve servir exclusivamente em `localhost` por padrão — não exposta à rede externa sem configuração explícita
NFR12: Nenhum dado pessoal ou sensível de usuários reais é processado — apenas o dataset público CICIDS2017 e dados simulados gerados por Isabela

### Additional Requirements

**Da Arquitetura:**
- Starter Template obrigatório: dois scaffoldings independentes — (A) `npm create vite@latest dashboard -- --template react-ts` para o Dashboard React e (B) Cookiecutter Data Science + FastAPI para o ML Pipeline. A inicialização dos dois componentes deve ser a **primeira história de implementação** (Epic 1 Story 1)
- Estrutura de repositório monorepo: `ic-ml-cybersecurity/ml-pipeline/` + `ic-ml-cybersecurity/dashboard/`
- Validação de schema CSV com Pydantic + pandera (pydantic 2.x + pandera 0.20.x)
- Serialização de modelos sklearn via `joblib` e Keras via `.h5` — pipeline completo embutido (scaler + encoder + modelo)
- Rastreamento de experimentos via `mlflow.sklearn.autolog()` e `mlflow.tensorflow.autolog()` — nomenclatura de experimentos: `ic-ml-cybersecurity-{model_type}`
- Contrato REST FastAPI → React: endpoints `POST /predict`, `GET /health`, `GET /model/info`, `GET /history`
- Comunicação real-time por polling com intervalo configurável (padrão 5s) via TanStack Query v5
- Configuração centralizada em `config.py` com variáveis: `RANDOM_SEED=42`, `WINDOW_SIZE`, `CONFIDENCE_THRESHOLD`, `MODEL_PATH`
- Estrutura de erros padronizada: exceções tipadas em Python (`PredictionError`, `ModelNotLoadedError`, `InvalidFeaturesError`) + handler global FastAPI
- Timestamps sempre em ISO 8601 em toda API e logs
- Logging Python via módulo `logging` padrão — nunca `print()` em produção

**Da UX:**
- Tema escuro obrigatório (bg-base `#0F1117`) com paleta semântica: critical `#EF4444`, warning `#F59E0B`, safe `#10B981`, info `#3B82F6`
- Severidade nunca comunicada apenas por cor — sempre acompanhada de ícone e label textual (acessibilidade WCAG AA)
- Tipografia: Inter para interface geral + JetBrains Mono para dados técnicos (IPs, timestamps, features)
- Layout: Sidebar fixa 220px + área principal fluida; 4 cards de métricas no header (alertas ativos, janelas analisadas, precisão do modelo, latência)
- Painel de detalhe de alerta inline (sem navegação para outra página): exibe tipo de ataque + confiança + top 3 features + ações (Confirmar / Falso Positivo / Ver Histórico)
- Ação "desfazer" disponível por 5 segundos via toast após decisão em alerta
- Seção "Modelos" com tabela comparativa RF / DT / LSTM com highlight do melhor e exportação CSV
- Modo de demonstração/replay de sessão histórica acessível em um clique na seção Modelos
- Badge de contagem de alertas ativos no título da aba do browser
- Responsividade: desktop-first; sidebar colapsável em telas menores

### FR Coverage Map

| FR | Épico | Descrição |
|---|---|---|
| FR1 | Epic 1 | Aceitar dataset CSV com features CICIDS2017 normalizadas |
| FR2 | Epic 1 | Validar formato do CSV de entrada |
| FR3 | Epic 1 | Dividir dados em treino e teste antes de qualquer transformação |
| FR4 | Epic 2 | Feature selection sobre conjunto de treino |
| FR5 | Epic 2 | Transformar sequências em sliding window |
| FR6 | Epic 2 | Aplicar sliding window separadamente em treino e teste |
| FR7 | Epic 2 | Configurar tamanho N da janela deslizante |
| FR8 | Epic 3 | Treinar modelo Random Forest |
| FR9 | Epic 3 | Treinar modelo Decision Tree |
| FR10 | Epic 3 | Treinar modelo LSTM ou MLP |
| FR11 | Epic 3 | Avaliar com k-fold cross-validation |
| FR12 | Epic 3 | Calcular F1, AUC-ROC, Precision, Recall, FPR |
| FR13 | Epic 3 | Reportar métricas com média e desvio padrão dos folds |
| FR14 | Epic 3 | Produzir tabela comparativa de métricas |
| FR15 | Epic 3 | Configurar hiperparâmetros antes do treino |
| FR16 | Epic 3 | Registrar automaticamente parâmetros de cada run (MLflow) |
| FR17 | Epic 3 | Registrar automaticamente métricas de cada run (MLflow) |
| FR18 | Epic 3 | Comparar múltiplos runs em painel de rastreamento |
| FR19 | Epic 3 | Exportar resultados em CSV para artigo |
| FR20 | Epic 4 | Serializar modelo com pipeline de pré-processamento completo |
| FR21 | Epic 4 | Selecionar e exportar modelo vencedor |
| FR22 | Epic 4 | Artefato exportado inclui scaler, window transformer e encoder |
| FR23 | Epic 4 | Expor endpoint `POST /predict` |
| FR24 | Epic 4 | Endpoint retorna tipo de ameaça, confiança e modelo |
| FR25 | Epic 4 | Documentação interativa `GET /docs` |
| FR26 | Epic 4 | Endpoint mock para desenvolvimento paralelo |
| FR27 | Epic 5 | Exibir tipo de ameaça, confiança, timestamp e modelo no alerta |
| FR28 | Epic 5 | Histórico de ≥ 100 notificações com status |
| FR29 | Epic 5 | Configurar threshold de confiança e registrar feedback por alerta |
| FR30 | Epic 1 | Garantir reprodutibilidade com seed configurável fixo |
| FR31 | Epic 1 | Documentar dependências com versões fixadas |
| FR32 | Epic 1 | README com instruções de instalação e execução |
| FR33 | Epic 3 | Gerar relatório de desempenho exportável para artigo |

## Epic List

### Epic 1: Fundação — Ambiente, Repositório e Contrato de Dados

Emili consegue inicializar o monorepo completo com os dois projetos (ML Pipeline + Dashboard React), configurar o ambiente reprodutível com seed fixo e dependências versionadas, e validar/carregar os dados do CICIDS2017 com o contrato formal de interface entre Caroline e Emili.

**FRs cobertos:** FR1, FR2, FR3, FR30, FR31, FR32
**NFRs cobertos:** NFR5, NFR6, NFR7, NFR9
**Nota arquitetural:** A primeira história inicializa os dois starters (Cookiecutter Data Science + FastAPI para `ml-pipeline/` e Vite + React + TypeScript para `dashboard/`).

---

### Epic 2: Pipeline de Feature Engineering

Emili consegue preparar os dados do CICIDS2017 para treinamento — executando feature selection sobre o conjunto de treino e transformando as sequências em janelas deslizantes (sliding window), com garantia de ausência de data leakage entre treino e teste.

**FRs cobertos:** FR4, FR5, FR6, FR7
**NFRs cobertos:** NFR5

---

### Epic 3: Treinamento, Avaliação e Rastreamento de Experimentos

Emili consegue treinar os três modelos (RF, DT, LSTM/MLP) com k-fold k=5, avaliar comparativamente com todas as métricas científicas exigidas (F1, AUC-ROC, Precision, Recall, FPR reportadas com média e desvio padrão), rastrear automaticamente todos os experimentos no MLflow e exportar resultados em CSV para o artigo científico.

**FRs cobertos:** FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR19, FR33
**NFRs cobertos:** NFR3, NFR4, NFR5

---

### Epic 4: Exportação do Modelo e Serviço de Predição

Emili consegue exportar o modelo vencedor com todo o pipeline de pré-processamento embutido (scaler + encoder + modelo) e disponibilizá-lo via FastAPI (`POST /predict`, `GET /health`, `GET /model/info`, `GET /history`, `GET /docs`) para consumo imediato pelo dashboard da Isabela — incluindo endpoint mock para desenvolvimento paralelo.

> ⚠️ **ORDEM:** Story 4.4 (Mock) deve ser implementada primeiro para habilitar o Epic 5 em paralelo.

**FRs cobertos:** FR20, FR21, FR22, FR23, FR24, FR25, FR26
**NFRs cobertos:** NFR1, NFR2, NFR8, NFR10, NFR11

---

### Epic 5: Dashboard de Monitoramento e Alertas

O analista de segurança (e a pesquisadora na demo do seminário) consegue monitorar previsões de ataques em tempo real via interface visual em tema escuro (Command Center), receber alertas com tipo de ameaça + nível de confiança + top features motivadoras, gerenciar histórico com feedback (confirmar / falso positivo), configurar threshold de confiança e comparar desempenho dos modelos (RF / DT / LSTM) — com modo de demonstração/replay para o seminário de IC.

**FRs cobertos:** FR27, FR28, FR29
**NFRs cobertos:** NFR12
**UX coberta:** Todos os requisitos do documento UX (tema escuro, sidebar fixa, Command Center, AlertCard com severidade, painel de detalhe inline com FeatureExplainer, tabela comparativa de modelos, modo demo).
**Growth feature (Story 5.7):** SlidingWindowChart — gráfico da janela temporal no painel de detalhe (pós-MVP se prazo permitir).

---

## Epic 1: Fundação — Ambiente, Repositório e Contrato de Dados

Emili consegue inicializar o monorepo completo com os dois projetos (ML Pipeline + Dashboard React), configurar o ambiente reprodutível com seed fixo e dependências versionadas, e validar/carregar os dados do CICIDS2017 com o contrato formal de interface entre Caroline e Emili.

### Story 1.1: Inicialização do Monorepo e Scaffolding dos Projetos
> **Status: ✅ CONCLUÍDA** — `ml-pipeline/` e `dashboard/` scaffoldados, estrutura de diretórios completa, `requirements.txt`, `README.md`, `config.py`, FastAPI `/health` funcionando.

Como pesquisadora de IC,
Quero inicializar o repositório monorepo com os dois projetos scaffoldados (ML Pipeline e Dashboard React),
Para que toda a equipe parta de uma base estruturada, padronizada e pronta para desenvolvimento.

**Acceptance Criteria:**

**Dado** que estou na raiz do projeto
**Quando** executo os comandos de inicialização descritos no README
**Então** o diretório `ml-pipeline/` existe com estrutura Cookiecutter Data Science + `src/api/` adicionado manualmente
**E** o diretório `dashboard/` existe com Vite + React + TypeScript + Tailwind CSS + shadcn/ui + Recharts instalados
**E** `ml-pipeline/requirements.txt` lista todas as dependências com versões fixadas
**E** `dashboard/package.json` lista todas as dependências com versões fixadas
**E** ambos os projetos iniciam sem erros (`uvicorn src/api/main:app` e `npm run dev`)

### Story 1.2: Configuração da Reprodutibilidade Científica
> **Status: ✅ CONCLUÍDA** — `src/utils/seed.py` com `set_global_seed()`, `RANDOM_SEED=42` em `config.py`, `CONFIDENCE_THRESHOLD=0.8`, testes de reprodutibilidade completos em `tests/test_reproducibility.py`.

Como pesquisadora de IC,
Quero um sistema com seed global fixo e dependências documentadas,
Para que qualquer experimento seja 100% reprodutível em qualquer máquina.

**Acceptance Criteria:**

**Dado** que o `ml-pipeline/` está scaffoldado
**Quando** abro `config.py`
**Então** `RANDOM_SEED = 42` está definido como constante
**E** `WINDOW_SIZE`, `CONFIDENCE_THRESHOLD` e `MODEL_PATH` estão definidos como variáveis configuráveis
**E** `.env.example` existe com todas as variáveis de ambiente documentadas
**E** executando o pipeline duas vezes com os mesmos dados, as métricas são idênticas (variação ≤ 0.01%)

### Story 1.3: Ingestão e Validação do Dataset CICIDS2017
> **Status: ✅ CONCLUÍDA** — `src/data/data_loader.py` (carrega Parquet model-ready, suporte a CIC e UNSW) + `src/data/data_validator.py` (validação de NaN, infinitos, Binary_Label) + pipeline completo em `src/data/pipeline/` (collector, cleaner, scaler, preprocessor) + testes em `tests/test_data_loader.py`. ⚠️ Formato alterado de CSV para Parquet (decisão registrada na arquitetura §12.1).

Como pesquisadora de ML (Emili),
Quero carregar e validar o dataset CSV do CICIDS2017 com verificação de schema formal,
Para que erros de formato ou dados inválidos sejam detectados antes do treinamento.

**Acceptance Criteria:**

**Dado** que existe um CSV válido em `data/processed/` com o contrato de Caroline
**Quando** executo `data_loader.py`
**Então** o dataset é carregado com todas as features esperadas presentes
**E** colunas faltantes ou com tipos incorretos geram erro descritivo imediato
**E** valores nulos são detectados e reportados (não silenciados)

**Dado** que o CSV tem colunas incorretas ou faltando a coluna `Label`
**Quando** executo `data_loader.py`
**Então** uma exceção clara é lançada informando quais colunas estão ausentes ou inválidas

### Story 1.4: Divisão Train/Test Estratificada e Formalização do Contrato de Dados
> **Status: 🔴 NÃO INICIADA** — `src/data/` tem data_loader e data_validator mas o módulo de split train/test e o `features_schema.json` ainda não foram implementados.

Como pesquisadora de ML (Emili),
Quero dividir os dados em treino e teste antes de qualquer transformação e formalizar o schema de interface com Caroline,
Para que não haja data leakage e o contrato de dados esteja documentado formalmente.

**Acceptance Criteria:**

**Dado** que o dataset foi carregado e validado (Story 1.3)
**Quando** executo a divisão train/test
**Então** o split ocorre estratificado por label com `random_state=config.RANDOM_SEED`
**E** nenhuma transformação (normalização, feature selection, sliding window) foi aplicada antes do split
**E** o arquivo `data/schema/features_schema.json` documenta formalmente: nomes das colunas, tipos, encoding dos labels e norma de tratamento de nulos

**Dado** que executo o split com o mesmo seed em duas execuções
**Quando** verifico os índices do conjunto de teste
**Então** os conjuntos são idênticos nas duas execuções

### Story 1.5: README de Reprodutibilidade
> **Status: 🟡 PARCIAL** — `ml-pipeline/README.md` existe com instruções de instalação e execução da API. Faltam: instruções do pipeline de treino completo, referência ao MLflow UI e tempo de setup do experimento end-to-end.

Como pesquisador externo,
Quero instruções claras de instalação e execução do projeto,
Para que consiga reproduzir os experimentos principais em ≤ 30 minutos de setup.

**Acceptance Criteria:**

**Dado** que acesso o repositório pela primeira vez
**Quando** sigo o README da raiz do projeto
**Então** em ≤ 30 minutos consigo: clonar o repo, instalar dependências de `requirements.txt`, executar o pipeline de treino com dados de exemplo e ver as métricas no MLflow UI
**E** o README documenta: pré-requisitos, estrutura do monorepo, instruções para `ml-pipeline/` e `dashboard/`, e como executar cada componente independentemente

---

## Epic 2: Pipeline de Feature Engineering

Emili consegue preparar os dados do CICIDS2017 para treinamento — executando feature selection sobre o conjunto de treino e transformando as sequências em janelas deslizantes (sliding window), com garantia de ausência de data leakage entre treino e teste.

### Story 2.1: Feature Selection sobre o Conjunto de Treino
> **Status: 🔴 NÃO INICIADA** — `src/features/` existe mas contém apenas `__init__.py`. `feature_selector.py` não implementado.

Como pesquisadora de ML (Emili),
Quero executar feature selection sobre o conjunto de treino para selecionar as top-N features mais relevantes,
Para que o modelo treine com as features de maior poder preditivo, reduzindo ruído e dimensionalidade.

**Acceptance Criteria:**

**Dado** que o dataset foi dividido em treino e teste (Story 1.4)
**Quando** executo `feature_selector.py` com N e threshold configuráveis
**Então** é calculada a importância de features usando Random Forest sobre o treino
**E** as top-N features por importância (ou todas acima do threshold mínimo) são selecionadas
**E** a seleção ocorre exclusivamente sobre o conjunto de treino — sem acesso ao teste
**E** o conjunto de features selecionadas é persistido em arquivo para uso consistente no treino e no teste

**Dado** que executo feature selection duas vezes com o mesmo seed
**Quando** comparo o conjunto de features selecionadas
**Então** o resultado é idêntico nas duas execuções

### Story 2.2: Transformação em Sliding Window
> **Status: 🔴 NÃO INICIADA** — `feature_engineer.py` não implementado. `WINDOW_SIZE` está configurado em `config.py` mas a transformação ainda não existe.

Como pesquisadora de ML (Emili),
Quero transformar sequências de registros de tráfego em janelas deslizantes de tamanho N configurável,
Para que os modelos sequenciais (LSTM) capturem dependências temporais que precedem ataques.

**Acceptance Criteria:**

**Dado** que o conjunto de treino tem as features selecionadas (Story 2.1)
**Quando** executo `feature_engineer.py` com `WINDOW_SIZE=N` (onde N ∈ {5, 10, 20})
**Então** cada amostra resultante é uma janela de N registros consecutivos
**E** o label de cada janela é o label do último registro da janela (previsão do estado seguinte)
**E** a transformação é aplicada separadamente sobre treino e teste sem compartilhamento de registros entre conjuntos
**E** o tamanho N é lido de `config.WINDOW_SIZE` — não hardcoded

**Dado** que `WINDOW_SIZE=10`
**Quando** verifico as dimensões do dataset resultante
**Então** cada amostra tem shape `(10, num_features)` para modelos sequenciais (LSTM) e `(10 * num_features,)` para modelos tabulares (RF, DT)

### Story 2.3: Validação Anti-Leakage do Pipeline de Features
> **Status: 🔴 NÃO INICIADA** — Depende de 2.1 e 2.2. `tests/test_feature_engineer.py` não existe.

Como pesquisadora de IC,
Quero validar que o pipeline de features não vaza dados do teste para o treino,
Para que a validade metodológica do experimento e a publicabilidade do artigo sejam garantidas.

**Acceptance Criteria:**

**Dado** que o pipeline de feature engineering foi executado (Stories 2.1 e 2.2)
**Quando** executo os testes de validação de leakage em `tests/test_feature_engineer.py`
**Então** nenhum índice do conjunto de teste aparece em janelas do conjunto de treino
**E** os parâmetros de feature selection (importâncias, threshold) foram calculados apenas com dados de treino
**E** os testes passam com resultado PASS sem exceções


---

## Epic 3: Treinamento, Avaliação e Rastreamento de Experimentos

Emili consegue treinar os três modelos (RF, DT, LSTM/MLP) com k-fold k=5, avaliar comparativamente com todas as métricas científicas exigidas (F1, AUC-ROC, Precision, Recall, FPR reportadas com média e desvio padrão), rastrear automaticamente todos os experimentos no MLflow e exportar resultados em CSV para o artigo científico.

### Story 3.1: Setup do MLflow e Infraestrutura de Rastreamento
> **Status: 🟡 PARCIAL** — `mlflow` está no `requirements.txt` e o diretório `mlruns/` existe (gerado automaticamente). Falta: configuração explícita do `mlflow.sklearn.autolog()`, nomenclatura de experimentos `ic-ml-cybersecurity-{model_type}` e script de setup.

Como pesquisadora de ML (Emili),
Quero configurar o MLflow local com nomenclatura padronizada de experimentos,
Para que todos os runs de treino sejam automaticamente rastreados sem boilerplate adicional.

**Acceptance Criteria:**

**Dado** que o `ml-pipeline/` está configurado (Epic 1)
**Quando** executo qualquer script de treino
**Então** o MLflow cria automaticamente um experimento nomeado `ic-ml-cybersecurity-{model_type}`
**E** `mlflow.sklearn.autolog()` ou `mlflow.tensorflow.autolog()` está ativo — registrando parâmetros e métricas sem código explícito
**E** `mlflow ui` exibe os runs em `http://localhost:5000`
**E** o diretório `mlruns/` é criado em `ml-pipeline/` e está no `.gitignore`

### Story 3.2: Treino e Avaliação do Random Forest com k-fold
> **Status: 🔴 NÃO INICIADA** — `src/training/` existe mas contém apenas `__init__.py`. `train_rf.py` não implementado.

Como pesquisadora de ML (Emili),
Quero treinar o Random Forest com k-fold k=5 e registrar todas as métricas científicas no MLflow,
Para que tenha evidência empírica replicável do desempenho do RF para o artigo.

**Acceptance Criteria:**

**Dado** que os dados com sliding window estão prontos (Epic 2) e o MLflow está configurado (Story 3.1)
**Quando** executo `train_rf.py` com hiperparâmetros configuráveis
**Então** o RF é treinado com k-fold cross-validation (k=5, `random_state=config.RANDOM_SEED`)
**E** para cada fold são calculados: F1-Score, AUC-ROC, Precision, Recall e FPR
**E** o MLflow registra automaticamente: algoritmo, hiperparâmetros, tamanho da janela e todas as métricas
**E** o resultado final reporta média ± desvio padrão de cada métrica entre os 5 folds
**E** o treino completo do RF sobre CICIDS2017 termina em ≤ 2 horas em CPU (Intel Core i5, 8GB RAM)

### Story 3.3: Treino e Avaliação do Decision Tree com k-fold
> **Status: 🔴 NÃO INICIADA** — `train_dt.py` não implementado.

Como pesquisadora de ML (Emili),
Quero treinar o Decision Tree com k-fold k=5 nas mesmas condições do RF,
Para que a comparação entre algoritmos seja metodologicamente válida (mesmo split, mesmo seed, mesmas features).

**Acceptance Criteria:**

**Dado** que os dados com sliding window estão prontos (Epic 2) e o MLflow está configurado (Story 3.1)
**Quando** executo `train_dt.py` com hiperparâmetros configuráveis
**Então** o DT é treinado com k-fold k=5 usando o mesmo split do RF (mesmo `random_state`)
**E** são calculados e registrados no MLflow: F1, AUC-ROC, Precision, Recall, FPR com média ± desvio padrão
**E** o experimento MLflow está sob o nome `ic-ml-cybersecurity-decision_tree`

### Story 3.4: Treino e Avaliação do LSTM/MLP com k-fold
> **Status: 🔴 NÃO INICIADA** — `train_lstm.py` não implementado. TensorFlow/Keras não está no `requirements.txt` ainda (usar Google Colab ou instalar localmente).

Como pesquisadora de ML (Emili),
Quero treinar o LSTM (ou MLP como fallback) com k-fold k=5 nas mesmas condições dos modelos anteriores,
Para que a comparação temporal vs. tabular tenha suporte empírico sólido.

**Acceptance Criteria:**

**Dado** que os dados em formato sequencial `(N, num_features)` estão prontos (Story 2.2)
**Quando** executo `train_lstm.py` — preferencialmente no Google Colab (GPU T4)
**Então** o LSTM é treinado com k-fold k=5, `tf.random.set_seed(config.RANDOM_SEED)` ativo
**E** são calculados e registrados no MLflow: F1, AUC-ROC, Precision, Recall, FPR com média ± desvio padrão
**E** o treino completo termina em ≤ 4 horas no Google Colab (GPU T4 gratuita)
**E** se LSTM for inviável no prazo, MLP é executado como substituto e documentado explicitamente no relatório

### Story 3.5: Tabela Comparativa de Métricas e Exportação CSV
> **Status: 🔴 NÃO INICIADA** — Depende de 3.2, 3.3, 3.4. `evaluator.py` não implementado.

Como pesquisadora de IC (Emili),
Quero gerar a tabela comparativa de desempenho entre RF, DT e LSTM e exportá-la em CSV,
Para que tenha a evidência empírica central do artigo científico formatada para publicação.

**Acceptance Criteria:**

**Dado** que todos os três modelos foram treinados e avaliados (Stories 3.2, 3.3, 3.4)
**Quando** executo `evaluator.py` ou abro o MLflow UI
**Então** uma tabela comparativa é exibida com RF, DT e LSTM como linhas e F1, AUC-ROC, Precision, Recall, FPR como colunas (média ± desvio padrão)
**E** o melhor modelo em cada métrica está destacado na tabela
**E** a tabela é exportável em CSV via comando CLI
**E** o CSV exportado é compatível com importação direta em LaTeX/Word para o artigo

### Story 3.6: Relatório de Desempenho por Tipo de Ataque
> **Status: 🔴 NÃO INICIADA** — Depende de 3.2–3.4.

Como pesquisadora de IC (Emili),
Quero gerar um relatório de desempenho dos modelos por tipo de ataque do CICIDS2017,
Para que o artigo científico apresente análise granular além das métricas agregadas.

**Acceptance Criteria:**

**Dado** que os modelos foram avaliados (Stories 3.2–3.4)
**Quando** executo a geração do relatório em `evaluator.py`
**Então** o relatório inclui F1, Precision, Recall e FPR por tipo de ataque (DDoS, Brute Force, PortScan, etc.)
**E** o relatório é exportável em CSV e/ou Markdown para inclusão no artigo
**E** o relatório identifica quais tipos de ataque cada modelo detecta melhor e pior

---

## Epic 4: Exportação do Modelo e Serviço de Predição

Emili consegue exportar o modelo vencedor com todo o pipeline de pré-processamento embutido (scaler + encoder + modelo) e disponibilizá-lo via FastAPI (`POST /predict`, `GET /health`, `GET /model/info`, `GET /history`, `GET /docs`) para consumo imediato pelo dashboard da Isabela — incluindo endpoint mock para desenvolvimento paralelo.

> ⚠️ **ORDEM DE IMPLEMENTAÇÃO:** Story 4.4 (Endpoint Mock) deve ser implementada **ANTES** das Stories 4.1–4.3. Isso habilita o desenvolvimento paralelo do Dashboard (Epic 5) sem aguardar o modelo real. Isabela pode iniciar o Epic 5 assim que Story 4.4 estiver concluída.

### Story 4.1: Serialização do Modelo Vencedor com Pipeline Completo
> **Status: 🔴 NÃO INICIADA** — `src/models/` existe com apenas `__init__.py`. `model_serializer.py` não implementado. Depende do Epic 3.

Como pesquisadora de ML (Emili),
Quero serializar o modelo vencedor junto com todo o pipeline de pré-processamento (scaler + encoder + modelo),
Para que a inferência funcione em qualquer ambiente limpo sem acesso ao código-fonte de treino.

**Acceptance Criteria:**

**Dado** que o modelo vencedor foi identificado (Epic 3)
**Quando** executo `model_serializer.py` para o modelo selecionado
**Então** o artefato exportado (`model_rf.pkl`, `model_dt.pkl` ou `model_lstm.h5`) contém o pipeline completo: scaler + window transformer + encoder + modelo
**E** o artefato é carregável em um ambiente Python limpo (sem o código de treino) com apenas `requirements.txt`
**E** uma predição de teste é executada com sucesso no ambiente limpo — confirmando portabilidade

**Dado** que tento carregar o artefato sem o scaler/encoder embutido
**Quando** executo inferência
**Então** a predição falha com erro descritivo indicando dependência faltante — não silencia o problema

### Story 4.2: Endpoint de Predição `POST /predict`
> **Status: 🔴 NÃO INICIADA** — `src/api/routes/` e `src/api/schemas/` existem mas contêm apenas `__init__.py`. `predict.py` não implementado.

Como sistema de alertas da Isabela,
Quero enviar uma janela de tráfego via HTTP e receber a predição do modelo,
Para que o dashboard exiba alertas em tempo real com tipo de ameaça e nível de confiança.

**Acceptance Criteria:**

**Dado** que a API está rodando em `http://127.0.0.1:8000`
**Quando** envio `POST /predict` com JSON contendo as features da janela de tráfego
**Então** a resposta retorna em ≤ 10 segundos com: `{ "prediction": "DDoS", "confidence": 0.94, "model": "random_forest", "timestamp": "2026-..T..Z" }`
**E** a resposta tem status HTTP 200 e Content-Type `application/json`
**E** todos os campos usam `snake_case` nos nomes

**Dado** que envio features inválidas (colunas faltando ou tipos errados)
**Quando** a API processa a requisição
**Então** retorna HTTP 422 com `{ "detail": "...", "code": "INVALID_FEATURES" }`

### Story 4.3: Endpoints de Saúde, Metadados e Histórico
> **Status: 🟡 PARCIAL** — `GET /health` implementado e funcional em `src/api/main.py`. Faltam: `GET /model/info`, `GET /history`, e carregamento do modelo no startup.

Como desenvolvedora do dashboard (Isabela),
Quero endpoints para verificar o estado da API, metadados do modelo ativo e histórico de predições,
Para que o dashboard mostre informações do sistema e o analista possa acessar predições anteriores.

**Acceptance Criteria:**

**Dado** que a API está rodando com modelo carregado
**Quando** envio `GET /health`
**Então** retorna HTTP 200 com status da API e nome do modelo carregado

**Quando** envio `GET /model/info`
**Então** retorna metadados do modelo ativo: tipo de algoritmo, WINDOW_SIZE, features utilizadas e data de treino

**Quando** envio `GET /history`
**Então** retorna lista das últimas predições com timestamp, prediction, confidence e model
**E** o modelo carrega em ≤ 5 segundos na inicialização da API (`uvicorn src/api/main:app --host 127.0.0.1 --port 8000`)

### Story 4.4: Endpoint Mock para Desenvolvimento Paralelo

> 🚀 **PRIORIDADE MÁXIMA — Implementar antes das Stories 4.1–4.3** (habilita Epic 5 em paralelo)
> **Status: 🔴 NÃO INICIADA** — ⚠️ **BLOQUEADOR do Epic 5.** `POST /predict/mock` não implementado. Isabela não pode iniciar o desenvolvimento do dashboard sem este endpoint.

Como desenvolvedora do dashboard (Isabela),
Quero um endpoint mock que retorna predições fixas sem depender do modelo real,
Para que possa desenvolver e testar a interface sem aguardar a conclusão do Epic 3.

**Acceptance Criteria:**

**Dado** que a API está rodando
**Quando** envio `POST /predict/mock`
**Então** retorna uma resposta no mesmo formato do `/predict` real, com dados simulados variados (diferentes tipos de ataque, diferentes níveis de confiança)
**E** o mock alterna ciclicamente entre pelo menos 3 tipos de resposta: ataque crítico, suspeito e tráfego normal
**E** a documentação interativa em `GET /docs` descreve ambos os endpoints (`/predict` e `/predict/mock`)

---

## Epic 5: Dashboard de Monitoramento e Alertas

O analista de segurança (e a pesquisadora na demo do seminário) consegue monitorar previsões de ataques em tempo real via interface visual em tema escuro (Command Center), receber alertas com tipo de ameaça + nível de confiança + features motivadoras, gerenciar histórico com feedback (confirmar / falso positivo), configurar threshold de confiança e comparar desempenho dos modelos (RF / DT / LSTM) — com modo de demonstração/replay para o seminário de IC.

> **Nota de reconciliação (2026-07-25):** revisado o protótipo isolado de Isabela na branch não mesclada `Isa252-patch-1` (Flask + Flask-SQLAlchemy + MySQL, modelo `Event` com `hora/categoria/severidade/origem/descricao`). Decisão: **manter a arquitetura oficial sem banco de dados** (já registrada em `architecture.md` — "banco de dados formal está fora do escopo desta IC"), descartando Flask/MySQL. Avaliação campo a campo:
> - `hora` → já coberto por `timestamp` (FR27, ISO 8601).
> - `categoria` → já coberto por "tipo de ameaça" (FR27); campo redundante.
> - `severidade` → já coberto e mais sofisticado no design oficial (badge de cor + ícone + label, derivado da confiança do modelo — ver `ux-design-specification.md`); nenhuma mudança necessária.
> - `origem` (fonte do evento) e `descricao` (texto livre) → **não portáveis**: o schema atual do CICIDS2017 pós feature-selection (`ml-pipeline/src/data/schema/features_schema.json`) não retém identificadores de origem (IP/host); adicionar esse campo exigiria reabrir o contrato de dados do Epic 1/2, fora do escopo desta reconciliação.
> - Cards de resumo ("Nº de Eventos", "Tipos de Anomalia") → conceito já absorvido pelos 4 cards de métrica do header da Story 5.1 (alertas ativos, janelas analisadas, precisão do modelo, latência).
>
> **Conclusão:** o contrato de alertas oficial (FR27–FR29, Stories 5.1–5.5) já cobre ou supera tudo que era estruturalmente viável no protótipo. Nenhuma alteração de schema foi necessária — o valor do protótipo foi confirmar, por validação independente, que o design já planejado está correto.

### Story 5.1: Scaffolding do Dashboard e Layout Command Center
> **Status: 🔴 NÃO INICIADA** — Scaffolding técnico existe (Vite + React + TS + Tailwind + shadcn + recharts + TanStack Query + `src/config.ts` + `src/services/api.ts`). Porém `App.tsx` ainda é o template padrão do Vite. A UI do dashboard (sidebar, header, tema escuro) não foi implementada.

Como desenvolvedora do dashboard (Isabela),
Quero o layout base do dashboard com sidebar fixa, header de métricas e tema escuro configurado,
Para que todas as histórias seguintes tenham uma estrutura visual consistente para construir.

**Acceptance Criteria:**

**Dado** que o projeto `dashboard/` está scaffoldado (Story 1.1)
**Quando** executo `npm run dev` e abro `http://localhost:5173`
**Então** a interface exibe sidebar fixa (220px) com 4 seções: Monitor, Alertas, Histórico, Modelos
**E** o tema escuro está ativo com `bg-base: #0F1117` como fundo principal
**E** o header exibe 4 cards de métricas: alertas ativos, janelas analisadas, precisão do modelo e latência
**E** as fontes Inter (interface) e JetBrains Mono (dados técnicos) estão aplicadas
**E** nenhum dado pessoal ou sensível é processado — apenas dados simulados/públicos (NFR12)

### Story 5.2: Integração com API via Polling e Exibição de Alertas em Tempo Real
> **Status: 🔴 NÃO INICIADA** — Depende de 5.1 e 4.4 (mock). `src/services/api.ts` existe como base, mas hooks e componentes não implementados.

Como analista de segurança (Ana),
Quero receber alertas de ameaças previstas automaticamente no dashboard sem refresh manual,
Para que possa monitorar a rede de forma passiva e ser notificada antes da concretização de um ataque.

**Acceptance Criteria:**

**Dado** que a API FastAPI está rodando em `http://127.0.0.1:8000` (real ou mock)
**Quando** abro o dashboard na seção Monitor
**Então** o TanStack Query faz polling a cada 5 segundos (configurável via `POLLING_INTERVAL_MS` em `src/config.ts`) em `GET /history`
**E** novos alertas aparecem automaticamente na lista sem refresh da página
**E** cada AlertCard exibe: tipo de ameaça, nível de confiança (%), timestamp da janela e badge de severidade por cor (critical `#EF4444` / warning `#F59E0B` / safe `#10B981`)
**E** a severidade é comunicada com cor + ícone + label textual — nunca apenas cor isolada (acessibilidade WCAG AA)
**E** o badge de contagem de alertas ativos no título da aba do browser atualiza em tempo real

### Story 5.3: Painel de Detalhe do Alerta com Ações de Decisão
> **Status: 🔴 NÃO INICIADA** — Depende de 5.2.

Como analista de segurança (Ana),
Quero clicar em um alerta e ver seus detalhes completos com opções de decisão inline,
Para que possa avaliar a ameaça e agir em ≤ 2 cliques sem sair do dashboard.

**Acceptance Criteria:**

**Dado** que há alertas na lista da seção Monitor
**Quando** clico em um AlertCard
**Então** um painel de detalhe abre inline (sem navegação para outra página) exibindo: tipo de ataque previsto, nível de confiança (%), janela temporal (timestamp início–fim) e identificador do modelo que gerou a predição
**E** o painel exibe as top 3 features de tráfego que motivaram a predição (nome em monospace + valor observado + delta vs. baseline)
**E** três botões de ação estão visíveis e funcionais: Confirmar (alerta é ameaça real) / Falso Positivo / Ver Histórico
**E** após a decisão, um toast aparece por 5 segundos com opção de desfazer a ação
**E** o alerta tratado muda de cor/estado imediatamente sem recarregar a página

### Story 5.4: Histórico de Alertas com Filtros e Feedback do Analista
> **Status: 🔴 NÃO INICIADA** — Depende de 5.3 e `GET /history` (Story 4.3).

Como analista de segurança (Ana),
Quero acessar o histórico completo de alertas tratados com status e poder registrar feedback,
Para que possa auditar decisões passadas e calibrar minha confiança no modelo ao longo do tempo.

**Acceptance Criteria:**

**Dado** que estou na seção Histórico do dashboard
**Quando** a seção carrega
**Então** são exibidas as últimas ≥ 100 notificações com: tipo de ameaça, nível de confiança, timestamp e status (confirmado / falso positivo / pendente)
**E** alertas confirmados e falsos positivos têm indicação visual distinta
**E** posso filtrar por status e por tipo de ameaça
**E** o registro de feedback de cada alerta fica vinculado ao alerta no histórico para análise posterior

### Story 5.5: Configuração de Threshold e Painel de Comparação de Modelos
> **Status: 🔴 NÃO INICIADA** — Depende de 5.1 e dados de avaliação do Epic 3.

Como analista de segurança (Ana) e pesquisadora (Isabela),
Quero configurar o threshold mínimo de confiança para disparo de alertas e comparar visualmente o desempenho dos modelos,
Para que possa calibrar o sistema para minha rede e apresentar os resultados científicos no seminário de IC.

**Acceptance Criteria:**

**Dado** que estou na seção Modelos do dashboard
**Quando** a seção carrega
**Então** uma tabela comparativa exibe RF, DT e LSTM com métricas: F1, AUC-ROC, Precision, Recall, FPR — e o melhor modelo por métrica está destacado
**E** um controle de threshold permite ajustar o valor mínimo de confiança para disparo de alertas (padrão: 90%)
**E** alertas abaixo do threshold configurado não aparecem na seção Monitor
**E** um botão "Exportar métricas CSV" faz download da tabela comparativa para o artigo

### Story 5.6: Modo de Demonstração para o Seminário de IC
> **Status: 🔴 NÃO INICIADA** — Depende de 5.2–5.5.

Como pesquisadora (Isabela),
Quero um modo de demonstração que reproduz sessões históricas de alertas em velocidade controlada,
Para que possa apresentar o sistema funcionando ao vivo no seminário de IC sem depender de tráfego real.

**Acceptance Criteria:**

**Dado** que estou na seção Modelos
**Quando** clico em "Modo Demo"
**Então** o dashboard inicia replay de uma sessão histórica pré-gravada, reproduzindo alertas em sequência com velocidade controlada (configurável: 1x, 2x, 4x)
**E** os alertas aparecem no Monitor como se fossem tempo real — com todos os cards, detalhes e ações funcionais
**E** o modo demo é acessível em um único clique — sem setup adicional
**E** um banner visível indica "MODO DEMONSTRAÇÃO" para distinguir de dados ao vivo

### Story 5.7: Gráfico da Janela Deslizante no Painel de Detalhe (Pós-MVP)

> 📌 **Escopo:** Growth feature — implementar após conclusão das Stories 5.1–5.6 caso o prazo permita.
> **Status: 🔴 NÃO INICIADA** — Pós-MVP.

Como analista de segurança (Ana),
Quero ver um gráfico de barras da janela temporal de tráfego que gerou o alerta no painel de detalhe,
Para que possa visualizar o padrão de tráfego que motivou a predição e compreender o contexto da ameaça.

**Acceptance Criteria:**

**Dado** que o painel de detalhe de um alerta está aberto (Story 5.3)
**Quando** o componente `SlidingWindowChart` renderiza
**Então** um gráfico de barras exibe os N registros da janela temporal que gerou a predição
**E** as barras são coloridas semanticamente: normal (`#10B981`) / elevado (`#F59E0B`) / anômalo (`#EF4444`)
**E** a janela é renderizada via Recharts (`BarChart`) com legenda e anotação de anomalia
**E** o gráfico exibe os valores das features mais relevantes (top features do FeatureExplainer)

**Dado** que os dados da janela não estão disponíveis na resposta da API
**Quando** o componente tenta renderizar
**Então** exibe estado vazio com mensagem informativa — sem erro não tratado
