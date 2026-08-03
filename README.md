# ic-ml-cybersecurity

> **Iniciação Científica — FCET**
> Detecção temporal de ataques cibernéticos com Machine Learning
> Orientação: Prof. Dr. Daniel Couto Gatti

---

## Índice

1. [O que é este projeto](#1-o-que-é-este-projeto)
2. [Quem faz o quê](#2-quem-faz-o-quê)
3. [O que é o BMAD](#3-o-que-é-o-bmad)
4. [Estrutura do repositório](#4-estrutura-do-repositório)
5. [Setup inicial — faça isso antes de qualquer coisa](#5-setup-inicial--faça-isso-antes-de-qualquer-coisa)
6. [Documentos que você precisa ler](#6-documentos-que-você-precisa-ler)
7. [Como usar o BMAD no dia a dia](#7-como-usar-o-bmad-no-dia-a-dia)
8. [Fluxo de trabalho — do início ao fim](#8-fluxo-de-trabalho--do-início-ao-fim)
9. [Protocolos de colaboração](#9-protocolos-de-colaboração)
10. [Reprodução dos Experimentos](#10-reprodução-dos-experimentos)

---

## 1. O que é este projeto

Este repositório é o espaço de trabalho da nossa IC. O componente operacional usa aprendizado de máquina para **detectar tráfego malicioso em uma janela recente**. A previsão antecipada foi investigada separadamente, mas os dados disponíveis não contêm eventos independentes suficientes para sustentá-la como tarefa final.

**Os três componentes do sistema:**

| Componente | Responsável | O que faz |
|---|---|---|
| **Pipeline de dados** | Caroline | Coleta e preserva o UNSW-NB15 não escalonado com metadados temporais |
| **Pipeline de ML** | Emili | Validação temporal, seleção de atributos, RF/DT/LSTM e exportação |
| **Dashboard** | Isabela | Interface React de monitoramento, alertas em tempo real, demonstração no seminário |

**Entregáveis da IC:** artigo científico com comparação empírica dos algoritmos, relatório final e demonstração funcional no seminário.

---

## 2. Quem faz o quê

### Caroline — Dados
Responsável pelo Epic 1 (parcial) e pela entrega do dataset processado.

- Coleta e limpeza do UNSW-NB15, preservando `Stime`, `Ltime` e arquivo-fonte
- Preservação do Parquet não escalonado para ajuste sem vazamento em cada fold
- Validação do contrato de 43 atributos brutos e dos metadados temporais
- O contrato de interface (colunas, tipos, ausência de nulos) é documentado na arquitetura

### Emili — ML Pipeline
Responsável pelos Epics 1, 2, 3 e 4.

- Inicialização do monorepo e ambiente reprodutível
- Feature selection dentro de folds e janelas isoladas por sessão
- Treino e avaliação de Random Forest, Decision Tree e LSTM em folds temporais expansivos
- Holdout cronológico fechado, purga e auditoria por hashes
- Exportação do modelo vencedor e API FastAPI (`POST /predict`)

### Isabela — Dashboard
Responsável pelo Epic 5.

- Dashboard React com Vite + TypeScript
- Exibição de alertas em tempo real (polling a cada 5s)
- Histórico de alertas, threshold de confiança, feedback do analista
- Modo de demonstração para o seminário
- Pode desenvolver em paralelo usando o endpoint mock que a Emili disponibiliza (`POST /predict/mock`)

---

## 3. O que é o BMAD

**BMAD** (Breakthrough Method for Agile AI-Driven Development) é um método que estrutura o uso de IA (GitHub Copilot) para desenvolvimento de software. Em vez de pedir ao Copilot coisas aleatórias, o BMAD organiza o trabalho em **agentes** e **workflows** — cada um com um papel bem definido.

### Como funciona na prática

Você ativa um agente no Copilot Chat e ele assume aquele papel. Exemplos:

| Agente | Persona | Para que usar |
|---|---|---|
| **bmad-master** 🧙 | BMad Master | Ponto de entrada — mostra menu de tudo disponível |
| **dev** 💻 | Amelia | Implementar uma story (escrever código) |
| **sm** 🏃 | Bob | Criar a próxima story a partir dos epics |
| **qa** 🧪 | Quinn | Gerar testes para código existente |
| **architect** 🏗️ | Winston | Decisões de arquitetura |
| **tech-writer** 📚 | Paige | Documentação técnica |

### Como ativar um agente

No **Copilot Chat** (VS Code), clique no dropdown de agentes e selecione, por exemplo, `@bmad-master`. Ou use os slash commands: `/bmad-help`.

### O que são workflows

Workflows são sequências guiadas de passos. O agente te conduz passo a passo. Exemplos relevantes para a fase atual:

| Workflow | O que faz |
|---|---|
| `sprint-status` | Mostra o estado atual de todas as stories e epics |
| `create-story` | Cria a próxima story pronta para implementação |
| `dev-story` | Implementa uma story seguindo as tarefas e critérios de aceite |
| `code-review` | Revisa o código implementado de forma adversarial |
| `sprint-planning` | Gera/atualiza o arquivo de controle do sprint |

---

## 4. Estrutura do repositório

```
ic-ml-cybersecurity/
│
├── README.md                          ← você está aqui
│
├── docs/                              ← planos individuais de IC (PDFs/DOCXs originais)
│
├── _bmad/                             ← motor do BMAD (não edite)
│   ├── bmm/
│   │   ├── config.template.yaml       ← template de configuração pessoal
│   │   └── config.yaml                ← SUA config local (não versionada, crie a partir do template)
│   ├── core/
│   │   ├── config.template.yaml
│   │   └── config.yaml                ← SUA config local
│   └── _memory/
│       ├── config.template.yaml
│       └── config.yaml                ← SUA config local
│
└── _bmad-output/                      ← todos os artefatos gerados pelo BMAD
    │
    ├── compartilhado/                 ← artefatos do PROJETO (lidas por todas)
    │   ├── planning-artifacts/
    │   │   ├── prd.md                 ⭐ PRD — requisitos do sistema
    │   │   ├── architecture.md        ⭐ Arquitetura técnica
    │   │   ├── epics.md               ⭐ Todos os epics e stories
    │   │   └── ux-design-specification.md
    │   └── implementation-artifacts/
    │       └── sprint-status.yaml     ⚠️ arquivo compartilhado — ver protocolos
    │
    ├── emili/                         ← artefatos pessoais da Emili
    ├── isabela/                       ← artefatos pessoais da Isabela
    └── caroline/                      ← artefatos pessoais da Caroline
```

> **Regra geral:** `compartilhado/` é o que todas precisam ver e respeitar. As pastas pessoais são para rascunhos, relatórios e artefatos individuais.

---

## 5. Setup inicial — faça isso antes de qualquer coisa

Execute estes comandos **uma única vez** após clonar o repositório. Substitua `{seu-nome}` por `isabela` ou `caroline` (em minúsculas).

### Passo 1 — Criar os arquivos de configuração pessoal

```bash
cp _bmad/core/config.template.yaml    _bmad/core/config.yaml
cp _bmad/bmm/config.template.yaml     _bmad/bmm/config.yaml
cp _bmad/_memory/config.template.yaml _bmad/_memory/config.yaml
```

### Passo 2 — Editar cada arquivo

Abra cada um dos três arquivos `config.yaml` criados e substitua **todas** as ocorrências de `{seu-nome}` pelo seu nome em minúsculas.

**Exemplo para Isabela** — como deve ficar o `_bmad/bmm/config.yaml`:

```yaml
project_name: ic-ml-cybersecurity
user_skill_level: intermediate
planning_artifacts: "{project-root}/_bmad-output/isabela/planning-artifacts"
implementation_artifacts: "{project-root}/_bmad-output/compartilhado/implementation-artifacts"
project_knowledge: "{project-root}/docs"

user_name: isabela
communication_language: Portuguese
document_output_language: Portuguese
output_folder: "{project-root}/_bmad-output/isabela"
```

> ⚠️ **Atenção:** `implementation_artifacts` deve apontar para `compartilhado/implementation-artifacts` — **não mude esse caminho**. Apenas `user_name`, `planning_artifacts` e `output_folder` mudam com o seu nome.

### Passo 3 — Verificar

Abra o Copilot Chat, selecione o agente `bmad-master` e envie qualquer mensagem. Se aparecer uma saudação com **seu nome**, o setup está correto.

---

## 6. Documentos que você precisa ler

Leia nesta ordem antes de começar a implementar qualquer coisa:

| # | Documento | Caminho | Por que ler |
|---|---|---|---|
| 1 | **PRD** | `_bmad-output/compartilhado/planning-artifacts/prd.md` | Define **o que** o sistema faz, os requisitos funcionais e não-funcionais, e os limites do escopo |
| 2 | **Arquitetura** | `_bmad-output/compartilhado/planning-artifacts/architecture.md` | Define **como** o sistema é construído — stack, estrutura de pastas, contratos entre componentes, decisões técnicas |
| 3 | **Epics e Stories** | `_bmad-output/compartilhado/planning-artifacts/epics.md` | Lista **todas as tarefas** do projeto organizadas por epic, com critérios de aceite detalhados |
| 4 | **Sprint Status** | `_bmad-output/compartilhado/implementation-artifacts/sprint-status.yaml` | Mostra o estado atual de cada story (backlog / in-progress / done) |

> **Dica:** O PRD e a Arquitetura são documentos de referência — você vai consultá-los durante toda a implementação, não apenas no início.

> **Importante — sobre a Arquitetura:** as decisões de arquitetura foram tomadas pela Emili em colaboração com o BMAD, sem consulta prévia à Isabela e à Caroline. Se ao ler o documento você discordar de alguma decisão, tiver dúvidas ou sentir que algo não faz sentido para o seu escopo, **discuta com o agente `architect` (Winston)** — ele pode ajudar a avaliar o impacto de qualquer mudança. Se uma alteração fizer sentido, ela pode ser feita. Mas atenção: **quando um documento é alterado, todos os outros precisam ser revisados** — uma mudança na arquitetura pode afetar epics, stories e o PRD. Veja o protocolo de alteração de documentos na seção 9.

---

## 7. Como usar o BMAD no dia a dia

### Verificar o estado do projeto

Ative o agente `bmad-master` e execute o workflow `sprint-status`. Ele vai mostrar quais stories estão em andamento, prontas para dev, ou concluídas.

### Pegar uma story para implementar

1. Verifique o `sprint-status` para saber o que está disponível
2. Execute o workflow `create-story` para gerar o arquivo detalhado da story (com tarefas, critérios de aceite e contexto técnico)
3. Execute o workflow `dev-story` para implementar a story com o agente `dev` (Amelia)
4. Após implementar, execute `code-review` para revisar

### Estrutura de uma story

Cada story gerada pelo BMAD tem:
- **Objetivo** — o que precisa ser feito
- **Contexto** — referências ao PRD, arquitetura e stories anteriores
- **Tasks** — lista de tarefas técnicas ordenadas
- **Critérios de aceite** — o que deve estar funcionando ao terminar
- **Notas de implementação** — dicas e armadilhas conhecidas

### Dicas práticas

- Sempre leia a story **inteira** antes de começar a implementar
- O agente `dev` (Amelia) é ultra-objetivo — se precisar de explicação de alguma decisão técnica, use o agente `architect` (Winston)
- Se travar em algo, use `/bmad-help sua dúvida aqui` para orientação

---

## 8. Fluxo de trabalho — do início ao fim

```
┌─────────────────────────────────────────────────────────┐
│                    FASE ATUAL: Implementação            │
└─────────────────────────────────────────────────────────┘

1. git pull                          ← sempre antes de começar
2. sprint-status                     ← ver o que está disponível
3. Combinar com a equipe qual story cada uma vai pegar
4. create-story [story-id]           ← gera o arquivo da story
5. dev-story                         ← implementa
6. code-review                       ← revisa
7. Atualizar sprint-status.yaml      ← marcar story como done
8. git add + commit + push           ← avisar no grupo antes do push
```

**Epics e stories do projeto:**

| Epic | Título | Responsável principal |
|---|---|---|
| Epic 1 | Fundação — Ambiente, Repositório e Contrato de Dados | Emili + Caroline |
| Epic 2 | Pipeline de Feature Engineering | Emili |
| Epic 3 | Treinamento, Avaliação e Rastreamento de Experimentos | Emili |
| Epic 4 | Exportação do Modelo e Serviço de Predição | Emili |
| Epic 5 | Dashboard de Monitoramento e Alertas | Isabela |

> **Isabela:** você pode começar o Epic 5 usando o endpoint mock (Story 4.4) assim que ele estiver pronto, sem precisar esperar o modelo real.

---

## 9. Protocolos de colaboração

### Git

| Situação | Protocolo |
|---|---|
| Antes de começar qualquer coisa | `git pull` |
| Antes de fazer push | Avisar no grupo: *"vou fazer push agora"* |
| Arquivos na pasta `compartilhado/` | Não deixar alterações locais sem commit por mais de um dia |
| Conflito de merge | Resolver juntas — não force push |

### `sprint-status.yaml`

Este arquivo é **único e compartilhado**. Se duas pessoas editarem ao mesmo tempo, haverá conflito de merge.

**Regra:** apenas uma pessoa edita e faz commit desse arquivo por vez. Combine antes.

### Epics e stories (`epics.md`, `prd.md`, `architecture.md`)

São documentos de referência que foram construídos de forma colaborativa (Emili + BMAD). A Isabela e a Caroline não participaram dessas decisões — portanto, se algo parecer errado, incompleto ou inadequado para o seu escopo, **isso é esperado e pode ser discutido**.

**Protocolo para alterar um documento compartilhado:**

1. Discuta a mudança com o agente correspondente (`architect` para arquitetura, `pm` para PRD, `sm` para epics/stories)
2. Avalie o impacto — pergunte ao agente quais outros documentos são afetados
3. Combine com a equipe antes de commitar qualquer alteração
4. **Atualize todos os documentos impactados na mesma sessão** — uma mudança na arquitetura pode invalidar stories, e uma mudança no PRD pode exigir revisão de epics
5. Nunca deixe documentos em estado inconsistente entre si

### Pastas pessoais (`_bmad-output/{seu-nome}/`)

Sua pasta é sua. Commit e push à vontade — não conflita com as outras.

### Comunicação

- Sempre comunique quando for **iniciar**, **terminar** ou **travar** em uma story
- Se encontrar algo errado num documento compartilhado (PRD, arquitetura, epics), mencione antes de corrigir

### Dataset e arquivos grandes

Os dados brutos e processados **não são versionados no git**. Cada pesquisadora mantém os Parquets do UNSW-NB15 localmente.

| O que não está no git | Onde obter |
|---|---|
| Dataset UNSW-NB15 | Fonte pública do UNSW Canberra |
| Artefatos intermediários (`.joblib`, `.keras`, `.parquet`) | Gerados localmente pelo protocolo |

---

## 10. Reprodução dos Experimentos

Para reproduzir os experimentos científicos descritos no artigo:

**Pré-requisitos:** Python 3.12, pip, git e os Parquets do UNSW-NB15.

O sistema compara Random Forest, Decision Tree e LSTM sobre janelas de dez registros do UNSW-NB15. Pré-processamento e seleção são ajustados somente no treino de cada fold, e o teste é uma sessão futura fechada. A tarefa é detecção do estado corrente, não previsão antecipada.

**Para reproduzir:**
1. Siga as instruções em [`ml-pipeline/README.md`](ml-pipeline/README.md)
2. Use `RANDOM_SEED = 42` (padrão em `config.py`) para resultados exatos
3. Confira protocolo, métricas e hashes em `ml-pipeline/reports_temporal/unsw/`

**Componente Dashboard** *(Epic 5 — a implementar)*

Para rodar o ambiente de desenvolvimento do dashboard (requer Node.js 18+):

```bash
cd dashboard
npm install
npm run dev
# Acesse: http://localhost:5173
```

> ⚠️ O dashboard está em desenvolvimento (Epic 5). A integração com a API de predição ocorrerá nas Stories 5.2–5.3.

**Dataset principal:** UNSW-NB15, não versionado no repositório.

---

*Dúvidas? Use `/bmad-help sua dúvida` no Copilot Chat ou pergunte para a Emili.*
