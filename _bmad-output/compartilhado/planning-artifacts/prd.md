---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete', 'step-e-01-discovery', 'step-e-02-review', 'step-e-03-edit']
workflowStatus: 'complete'
completedAt: '2026-02-21'
lastEdited: '2026-02-21'
editHistory:
  - date: '2026-02-21'
    changes: 'Removido implementation leakage de FR18, FR20, FR30, FR31, NFR5, NFR6; refinado FR4 com critério mensurável; expandidos FR27-FR29 com requisitos de visualização; adicionado método de medição ao NFR10'
classification:
  projectType: 'ml-pipeline-web-interface'
  domain: 'scientific-cybersecurity'
  complexity: 'medium'
  projectContext: 'greenfield'
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-ic-ml-cybersecurity-2026-02-20.md"
  - "_bmad-output/planning-artifacts/research/domain-ml-cybersecurity-research-2026-02-20.md"
  - "docs/Plano individual - Emili Vieira Tabuti.pdf"
  - "docs/Plano individual de IC - Caroline.docx"
  - "docs/Plano individual-Isabela Groke Gomes.docx"
workflowType: 'prd'
---

# Product Requirements Document - ic-ml-cybersecurity

**Author:** Emili-tabuti
**Date:** 2026-02-20

---

## Executive Summary

Sistema de previsão antecipada de ataques cibernéticos baseado em Machine Learning, desenvolvido como Iniciação Científica no FCET sob orientação do Prof. Dr. Daniel Couto Gatti. O sistema analisa janelas temporais deslizantes de tráfego de rede para prever a ocorrência de ataques *antes* da sua concretização, emitindo alertas com latência ≤ 10 segundos. O projeto é conduzido por três pesquisadoras com escopos complementares: coleta e pré-processamento de dados (Caroline), implementação e comparação de modelos ML (Emili), e avaliação em ambiente simulado com interface de visualização (Isabela).

**Usuário-alvo:** Analista de segurança em redes acadêmicas que necessita de alertas proativos — não reativos — para agir antes da concretização de um ataque.

**Problema central:** Ferramentas tradicionais de detecção (Snort, Suricata, SIEM) operam sobre assinaturas fixas e detectam ameaças somente após o início do ataque. Redes acadêmicas permanecem expostas a ataques zero-day e ameaças emergentes sem mecanismo de antecipação.

**Entregáveis institucionais:** artigo científico com comparação empírica de algoritmos, relatório final de IC, e demonstração funcional em seminário.

### What Makes This Special

Enquanto sistemas baseados em regras *reagem*, este sistema *prevê*: modelos treinados em sequências temporais de features de tráfego de rede (sliding window sobre o CICIDS2017) aprendem padrões que precedem ataques, não apenas os caracterizam. A comparação empírica entre RF, DT e LSTM/RNN — sem hipótese pré-fixada — produz evidência científica sobre qual paradigma (deep learning temporal vs. ML tradicional tabular) é mais eficaz para previsão antecipada neste domínio.

**Insight central:** Previsão de ataques é um problema de série temporal, não de classificação estática. Modelos que capturam dependência temporal (LSTM/RNN) têm vantagem estrutural sobre modelos que tratam cada janela de tráfego de forma independente.

**Diferencial sobre a literatura:** 14 papers analisados focam em *detecção* (classificação de tráfego em andamento). Este trabalho aplica a abordagem de *previsão* (predição da janela seguinte) com sliding window — recorte menos explorado e com maior valor operacional.

### Project Classification

| Dimensão | Valor |
|---|---|
| **Tipo** | ML Pipeline + Interface de Monitoramento |
| **Domínio** | Científico — Cibersegurança |
| **Complexidade** | Média |
| **Contexto** | Greenfield |
| **Dataset principal** | CICIDS2017 |
| **Dataset comparativo** | NSL-KDD |
| **Modo de processamento** | Batch com sliding window |

---

## Success Criteria

### User Success

O sistema entrega valor quando o analista de segurança recebe um alerta *antes* da concretização do ataque, com informações suficientes para agir preventivamente. Sucesso do usuário é medido por:

- Alerta emitido com antecedência ao ataque — não após sua materialização
- Latência do alerta ≤ 10 segundos após processamento da janela de tráfego
- Taxa de falsos positivos ≤ 10% — o analista confia nos alertas recebidos
- Interface de visualização (Isabela) apresenta o alerta com tipo de ameaça e nível de confiança do modelo

### Business Success

Como projeto de IC, sucesso de negócio equivale às entregas científicas e institucionais:

| Entregável | Critério de Conclusão |
|---|---|
| Artigo científico | Submetido com comparação empírica de ≥ 3 algoritmos (RF, DT, LSTM) e resultados no CICIDS2017 |
| Relatório final de IC | Documentação completa do pipeline: dados → modelos → alertas → avaliação |
| Seminário | Demonstração funcional do sistema detectando ao menos 1 tipo de ataque simulado ao vivo |

### Technical Success

**Módulo ML (Emili) — critérios primários:**

| Métrica | Meta |
|---|---|
| Precision | ≥ 90% |
| Recall | ≥ 85% |
| F1-Score | Maximizar |
| AUC-ROC | ≥ 0.90 |
| False Positive Rate | ≤ 10% |
| Latência do alerta | ≤ 10 segundos |
| Validação | k-fold cross-validation, k=5 |
| Algoritmos comparados | ≥ 3 (RF, DT + LSTM/MLP) |

**Sistema completo — critérios de integração:**
- Pipeline end-to-end funcional: dados normalizados (Caroline) → modelo treinado (Emili) → alerta disparado → visualização (Isabela)
- ≥ 1 cenário de ataque simulado detectado em dados ao vivo no ambiente da Isabela
- Cobertura de tipos de ataque: todos os tipos presentes no CICIDS2017 (subconjunto prioritário a definir por Isabela)

### Measurable Outcomes

- Melhor modelo identificado empiricamente dentre RF, DT e LSTM/MLP no CICIDS2017
- Comparação replicável: código, dataset e métricas documentados para reprodução
- Evidência publicável: F1-Score, AUC-ROC, Precision, Recall e FPR reportados por algoritmo, por tipo de ataque e no agregado

---

## Product Scope

### MVP — Minimum Viable Product

**Módulo ML (Emili — semanas 1–15):**
- Implementação de RF, DT e LSTM/MLP com scikit-learn e TensorFlow/Keras
- Treinamento com dados normalizados entregues pela Caroline (features do CICIDS2017)
- Feature selection sobre as 78 features do CICIDS2017
- Sliding window sobre sequências temporais de tráfego de rede
- Avaliação comparativa com k-fold (k=5): F1, AUC-ROC, Precision, Recall, FPR
- Integração do melhor modelo ao sistema de alerta da Isabela

**Módulo de Dados (Caroline — semanas 1–7):**
- Coleta, limpeza e normalização de dados do CICIDS2017
- Entrega de dados normalizados prontos para treinamento

**Módulo de Avaliação (Isabela — semanas 5–21):**
- Interface de visualização de alertas
- Ambiente de teste simulado
- Definição dos tipos de ataque a cobrir nos cenários

### Growth Features (Pós-MVP)

- NSL-KDD como dataset comparativo para validação cruzada entre benchmarks
- Métricas por janela temporal e por tipo de ataque individualizadas
- Exportação de relatórios de desempenho automatizados

### Vision (Futuro)

- **XAI (Explicabilidade):** SHAP ou LIME para mostrar *por que* o modelo classificou um tráfego como ataque — diferencial científico e valor operacional para o analista
- Retraining automático do modelo com novos dados
- Deploy em ambiente de produção com tráfego real da rede universitária
- Suporte a múltiplos contextos de rede além do acadêmico

---

## User Journeys

### Journey 1: Ana Souza — Analista de Segurança (Caminho de Sucesso)

**Persona:** Ana, 32 anos, analista de segurança numa universidade estadual. Ela protege a rede de 8.000 usuários com uma equipe pequena. Seu maior medo não é o ataque em si — é descobrir o ataque *depois* que os dados já foram comprometidos.

**Cena de abertura:** São 14h de uma terça-feira. Ana monitora dashboards do Snort enquanto gerencia 3 outros chamados abertos. O sistema gera 40–60 alertas por dia; ela ignora a maioria porque são falsos positivos. Ela está cansada de "alarmes de incêndio" que não são incêndios.

**Ação crescente:** Ana configura o sistema conectando-o à fonte de tráfego de rede já capturado. Seleciona o modelo pré-treinado e define o threshold de confiança mínimo para disparo de alertas.

**Clímax:** Às 16h23, o sistema processa a janela de tráfego atual e identifica um padrão que precede um ataque de Brute Force SSH nos últimos 3 registros históricos similares. Um alerta chega ao dashboard da Isabela: *"Ameaça prevista — Brute Force SSH — confiança 94% — janela de tráfego 16:22–16:23."* O ataque ainda não começou.

**Resolução:** Ana bloqueia o IP de origem. O ataque nunca se concretiza. Ela anota: *"Primeiro alerta útil que recebi em semanas."*

---

### Journey 2: Ana Souza — Caso de Borda (Falso Positivo)

**Cena de abertura:** O sistema emite um alerta de DDoS às 09h de uma segunda-feira. Ana investiga e percebe que é o backup automatizado semanal gerando um pico de tráfego interno atípico.

**Conflito:** O modelo classificou o padrão como precursor de DDoS com 78% de confiança. Ana quer saber *por que* o modelo tomou essa decisão — quais features pesaram mais.

**Resolução (MVP):** O alerta indica o nível de confiança (78%) — abaixo do limiar típico de 90%+. Ana aprende a calibrar o threshold para o contexto da sua rede. *(Nota: explicabilidade completa — SHAP/LIME — é roadmap futuro/XAI.)*

**Requisito revelado:** O sistema deve exibir o nível de confiança do modelo junto ao alerta para que o analista possa julgar a relevância.

---

### Journey 3: Emili — ML Engineer (Treino e Avaliação dos Modelos)

**Persona:** Emili, estudante de CC no 3º ano, aprendendo ML na prática pela primeira vez em produção real. Tem base teórica sólida, mas nunca treinou um modelo com dados de segurança reais.

**Cena de abertura:** Caroline entrega um CSV com as features do CICIDS2017 já normalizadas. Emili recebe o arquivo, abre no Jupyter Notebook e vê 78 colunas e ~2,8 milhões de registros. Primeira reação: *"Por onde começo?"*

**Ação crescente:** Emili aplica feature selection (ex: correlação + importância pelo RF) para reduzir as 78 features para as mais relevantes. Transforma os dados em janelas temporais deslizantes de N segundos para alimentar o LSTM. Treina RF, DT e LSTM com k-fold k=5.

**Clímax:** Após os treinos, gera a tabela comparativa de F1, AUC-ROC, Precision, Recall e FPR para RF, DT e LSTM. O LSTM supera os demais em F1 e Recall — mas RF empata em Precision com custo computacional muito menor. Emili tem evidência empírica para o artigo.

**Resolução:** Emili seleciona o LSTM como modelo de integração. Exporta o modelo serializado (`.pkl` / `.h5`) para a Isabela conectar ao sistema de alertas. Documenta a metodologia para o artigo.

---

### Journey 4: Caroline — Data Engineer (Entrega dos Dados)

**Persona:** Caroline, colega de IC responsável pelo módulo de dados. Seu trabalho termina onde o de Emili começa.

**Cena de abertura:** Caroline finaliza o pipeline de pré-processamento do CICIDS2017 no mês 7. Normaliza as features, remove duplicatas e garante que os labels de ataque estão corretos.

**Clímax:** Caroline entrega o dataset normalizado a Emili no formato acordado (CSV com colunas nomeadas seguindo a nomenclatura do CICIDS2017). Emili consegue carregar diretamente sem reprocessamento.

**Requisito revelado:** Interface de dados entre Caroline e Emili precisa ser acordada formalmente — formato, nomes de colunas, encoding dos labels, tratamento de valores nulos.

---

### Journey 5: Pesquisador/Estudante — Reprodução do Experimento

**Persona:** João, mestrando em segurança computacional, leu o artigo da IC e quer reproduzir os resultados com seu próprio dataset.

**Cena de abertura:** João acessa o repositório do projeto, lê o README e tenta reproduzir o pipeline de treino com o CICIDS2017.

**Resolução:** Com o código documentado e as instruções de uso, João consegue reproduzir os resultados publicados no artigo. Ele cita o trabalho e estende com um dataset diferente.

**Requisito revelado:** Código reprodutível com instruções claras de instalação, dependências e execução — requisito de qualidade científica.

---

### Journey Requirements Summary

| Jornada | Capacidades Reveladas |
|---|---|
| Ana — Sucesso | Alerta com tipo de ameaça + nível de confiança + timestamp da janela |
| Ana — Borda | Threshold configurável; nível de confiança visível no alerta |
| Emili — ML | Feature selection; sliding window; treino k-fold; exportação do modelo; tabela comparativa de métricas |
| Caroline → Emili | Contrato de interface de dados (formato CSV, colunas, labels) |
| Pesquisador | Código reprodutível; README; dependências documentadas |

---

## Domain-Specific Requirements

### Reprodutibilidade Científica

- Todo experimento deve ser reprodutível: código versionado, seed fixo para aleatoriedade (`random_state` fixo em todos os modelos)
- Dataset CICIDS2017 é público e deve ser citado formalmente no artigo
- Dependências do projeto documentadas em `requirements.txt` com versões fixadas
- Resultados reportados com média e desvio padrão do k-fold (k=5) — não apenas o melhor run

### Validade Metodológica

- **Separação rigorosa train/test:** nenhum dado de teste pode contaminar o treino (sem data leakage)
- **Sliding window** deve ser aplicada *após* a divisão train/test — janelas do conjunto de teste não podem incluir amostras do treino
- Feature selection executada apenas sobre o conjunto de treino — nunca com visibilidade do test set
- Comparação entre algoritmos feita nas mesmas condições: mesmo split, mesmo k-fold, mesmas features

### Restrições Computacionais

- **Ambiente primário:** notebook pessoal — CPU only, sem GPU dedicada
- **Implicação para LSTM:** treinamento pode ser lento; recomendado uso de Google Colab (GPU gratuita) ou Kaggle Notebooks para os experimentos com LSTM/RNN
- RF e DT são viáveis em CPU com o CICIDS2017 (~2,8M registros)
- Hiperparâmetros do LSTM devem ser escolhidos com atenção ao tempo de treino — grid search completo pode ser inviável em CPU

### Dataset e Privacidade

- **MVP usa exclusivamente CICIDS2017** (dataset público, sem dados reais da rede universitária)
- Captura de tráfego real da FCET é **fora do escopo do MVP** — requer aprovação institucional e levanta questões de privacidade dos usuários da rede
- Caso seja viável futuramente, requer anonimização e aprovação do comitê de ética da universidade

### Riscos de Domínio e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Data leakage no sliding window | Resultados inflados, artigo não reprodutível | Aplicar window apenas após split train/test |
| LSTM inviável em CPU no prazo | Entrega atrasada | Usar Colab/Kaggle para treino; CPU para experimentos menores |
| CICIDS2017 desbalanceado por classe | Métricas de accuracy enganosas | Usar F1, AUC-ROC e FPR — nunca accuracy isolada |
| Ataques adversariais (P6 — 2025) | Modelo enganado em produção | Mencionar como limitação no artigo — escopo futuro |
| Resultados não reprodutíveis | Artigo não publicável | Seed fixo + requirements.txt + README com instruções |

---

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. Paradigma de Previsão vs. Detecção**
Os 14 papers analisados na pesquisa bibliográfica focam exclusivamente em *intrusion detection* — classificação de tráfego que já está ocorrendo. Este trabalho aplica o paradigma de *previsão antecipada*: dado um histórico de janelas de tráfego, estimar a probabilidade de ataque na janela seguinte. É uma mudança fundamental de enquadramento do problema, com maior valor operacional (tempo de resposta para o analista) e menor exploração na literatura.

**2. Sliding Window como Estrutura de Previsão Temporal**
A abordagem de sliding window sobre sequências de features de tráfego de rede não é comum nos papers de IDS — a maioria trata cada fluxo de forma independente. Aplicar sliding window cria um contexto temporal que habilita modelos sequenciais (LSTM/RNN) a detectar padrões que precedem o ataque antes de ele se manifestar plenamente.

**3. Comparação Empírica no Paradigma de Previsão**
A comparação empírica entre LSTM/RNN e ML tradicional (RF, DT) é vasta na literatura de *detecção*. No paradigma de *previsão com sliding window*, essa comparação é inédita nos papers analisados — o artigo desta IC produz evidência nova sobre qual classe de modelos tem vantagem estrutural quando o problema é formulado como série temporal.

### Contexto de Mercado e Literatura

- Pesquisa bibliográfica (14 papers, 2017–2025) confirma: nenhum dos papers revisados aplica sliding window para *previsão* — todos classificam tráfego em andamento
- P5 (Yin et al., 2017) é o mais próximo: RNN-IDS trata dados de rede como sequência, mas para *detecção*, não *previsão*
- P6 (Ennaji et al., 2025): menciona previsão de comportamento como direção futura de pesquisa — validando a relevância do recorte escolhido
- Mercado de segurança (2024–2025) está migrando de SIEM reativo para plataformas de detecção/previsão baseadas em ML — momento certo para pesquisa acadêmica neste espaço

### Abordagem de Validação

- A inovação é validada empiricamente: se LSTM com sliding window superar RF e DT nas mesmas condições, o paradigma de previsão tem suporte empírico
- Se RF/DT superarem LSTM, o resultado também é publicável — evidência de que modelos tabulares são robustos mesmo no paradigma temporal
- Ambos os resultados contribuem para a literatura: a inovação está na *pergunta*, não necessariamente na *resposta*

### Mitigação de Riscos da Inovação

| Risco | Probabilidade | Mitigação |
|---|---|---|
| LSTM não supera RF no paradigma de previsão | Média | Resultado ainda publicável — contribuição científica independe da direção |
| Sliding window não captura padrões preditivos úteis | Baixa | Papers de séries temporais em IDS (P5) sugerem sinal temporal existe |
| Tamanho da janela (N) impacta muito os resultados | Alta | Testar múltiplos tamanhos de janela como hiperparâmetro — reportar sensibilidade |

---

## ML Pipeline — Specific Requirements

### Project-Type Overview

Sistema composto por três módulos independentes integrados via contratos de dados e API. O módulo ML (Emili) é o núcleo do pipeline: recebe dados normalizados, treina e avalia modelos, e expõe o modelo vencedor via REST API para o módulo de avaliação (Isabela). O rastreamento de todos os experimentos é feito via MLflow local.

### Arquitetura do Pipeline

```
[CICIDS2017 normalizado] → [Feature Selection] → [Sliding Window]
        ↓
[Treino k-fold k=5: RF | DT | LSTM]
        ↓
[Avaliação: F1, AUC-ROC, Precision, Recall, FPR]
        ↓
[MLflow: registro de todos os runs]
        ↓
[Modelo vencedor serializado: .pkl / .h5]
        ↓
[FastAPI: POST /predict → resposta com classe + confiança]
        ↓
[Módulo Isabela: alerta + visualização]
```

### Interface de Dados (Contrato Caroline → Emili)

| Campo | Especificação |
|---|---|
| Formato | CSV |
| Features | Subconjunto das 78 features do CICIDS2017 (após normalização) |
| Nomenclatura | Colunas seguem nome original do CICIDS2017 |
| Label | Coluna `Label` — valores: `BENIGN` + categorias de ataque |
| Encoding | Labels codificados como inteiros (label encoding) |
| Valores nulos | Removidos ou imputados por Caroline antes da entrega |
| Normalização | Min-Max ou Z-score — definido por Caroline, documentado |

### Rastreamento de Experimentos (MLflow)

- Ferramenta: **MLflow local** (`mlflow ui` no terminal)
- Cada run registra: algoritmo, hiperparâmetros, F1, AUC-ROC, Precision, Recall, FPR, tempo de treino
- Comparação visual entre todos os modelos via MLflow UI
- Experimentos exportados como CSV para inclusão no artigo

### Serialização do Modelo

| Algoritmo | Formato | Biblioteca |
|---|---|---|
| Random Forest | `.pkl` (Pickle) | scikit-learn |
| Decision Tree | `.pkl` (Pickle) | scikit-learn |
| LSTM / MLP | `.h5` (HDF5) | Keras / TensorFlow |

### Interface de Invocação (FastAPI)

- **Endpoint:** `POST /predict`
- **Input:** JSON com features da janela de tráfego (sliding window pré-processada)
- **Output:** `{ "prediction": "DDoS", "confidence": 0.94, "model": "LSTM" }`
- **Documentação automática:** disponível em `GET /docs`
- **Ambiente:** servidor local (`uvicorn main:app --host 0.0.0.0 --port 8000`)

### Considerações de Implementação

- **Sliding window:** tamanho N a ser definido empiricamente (testar N=5, N=10, N=20 janelas) — reportar sensibilidade no artigo
- **Feature selection:** método a definir (correlation matrix + RF feature importance como baseline)
- **Reprodutibilidade:** `random_state=42` em todos os modelos scikit-learn; `tf.random.set_seed(42)` para Keras
- **Ambiente:** Python 3.10+, dependências fixadas em `requirements.txt`
- **GPU:** experimentos LSTM via Google Colab quando necessário; restante em CPU local

---

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**Abordagem MVP:** Validação científica — o MVP é bem-sucedido quando produz evidência empírica comparável e publicável com pipeline funcional end-to-end.

**Prazo total:** 21 de fevereiro a 31 de julho de 2026 — **~23 semanas / 5 meses** para os 3 módulos.

**Algoritmos no MVP (revisado):** RF, DT e LSTM/MLP.
> SVM removido do escopo — menor contribuição científica frente aos demais; sua ausência libera tempo de implementação e análise sem comprometer o artigo. Scientific claim atualizado: *"Comparação empírica entre RF, DT e LSTM para previsão antecipada de ataques com sliding window no CICIDS2017."*

### Cronograma Revisado (23 semanas)

| Semanas | Período | Emili (ML) | Caroline (Dados) | Isabela (Avaliação) |
|---|---|---|---|---|
| 1–4 | Fev–Mar | Setup do ambiente, definição da sliding window, planejamento da feature selection | Coleta, limpeza e normalização do CICIDS2017 | Planejamento da interface e cenários de teste |
| 5–7 | Mar–Abr | Feature selection, implementação da sliding window, setup MLflow | **Entrega do dataset normalizado** | Início do desenvolvimento da interface |
| 8–12 | Abr–Mai | Treino RF, DT e LSTM com k-fold k=5; rastreamento MLflow | Suporte a dúvidas de dados | Desenvolvimento da interface de alertas |
| 12–15 | Mai–Jun | Avaliação comparativa, seleção do melhor modelo, implementação FastAPI | — | **Início da integração com o modelo via FastAPI** |
| 15–18 | Jun–Jul | Testes de integração com Isabela, documentação, escrita do artigo | — | Cenários de ataque simulados, testes de ponta a ponta |
| 19–21 | Jul 1–21 | Revisão final do artigo, relatório de IC, preparação do seminário | Relatório do módulo de dados | Relatório de avaliação final |
| 22–23 | Jul 22–31 | **Buffer:** ajustes finais, revisão do artigo, correções pós-integração | Buffer final | Buffer final |

> ⚠️ **Marco crítico:** Caroline deve entregar o dataset normalizado até a **semana 7 (final de março)**. Atrasos nesse marco impactam diretamente o tempo de Emili para treino e avaliação.

### MVP Feature Set — Entregas obrigatórias até 31/07/2026

**Módulo ML (Emili):**
- Feature selection sobre CICIDS2017
- Sliding window (testar N=5, N=10, N=20)
- Treino e avaliação de RF, DT e LSTM com k-fold k=5
- Métricas: F1, AUC-ROC, Precision, Recall, FPR — registradas no MLflow
- Modelo vencedor serializado (`.pkl` ou `.h5`)
- FastAPI `POST /predict` funcional

**Módulo de Dados (Caroline):**
- Dataset CICIDS2017 normalizado entregue até semana 7
- Contrato de interface documentado (formato, colunas, labels)

**Módulo de Avaliação (Isabela):**
- Interface de visualização de alertas
- ≥ 1 cenário de ataque simulado funcional
- Relatório de avaliação de desempenho

### Post-MVP Features (Trabalho Futuro)

- NSL-KDD como dataset comparativo
- Métricas por tipo de ataque individualizadas
- XAI: SHAP/LIME para explicabilidade do modelo
- Retraining automático com novos dados
- Deploy em rede universitária real (com aprovação institucional)

### Risk Mitigation Strategy

| Risco | Mitigação |
|---|---|
| **Caroline atrasa entrega do dataset** | Emili implementa pipeline completo com subset do CICIDS2017 raw como placeholder |
| **LSTM inviável em CPU no prazo** | Google Colab para treino; se ainda inviável, substituir por MLP |
| **Tempo insuficiente para todas as análises** | Priorizar: RF → DT → LSTM (nessa ordem) |
| **Integração com Isabela atrasada** | FastAPI mock com respostas fixas permite desenvolvimento paralelo |

---

## Functional Requirements

### 1. Ingestão e Preparação de Dados

- **FR1:** O sistema aceita como entrada um dataset CSV com features do CICIDS2017 normalizadas
- **FR2:** O sistema valida o formato do CSV de entrada (colunas esperadas, ausência de valores nulos)
- **FR3:** O sistema divide os dados em conjuntos de treino e teste antes de qualquer transformação

### 2. Feature Engineering e Seleção

- **FR4:** Emili pode executar feature selection sobre o conjunto de treino, selecionando as top-N features por importância (RF) ou correlação com o label, onde N e o threshold mínimo são configuráveis antes da execução
- **FR5:** O sistema transforma sequências de registros de tráfego em janelas deslizantes de tamanho configurável (sliding window)
- **FR6:** O sistema aplica sliding window separadamente sobre treino e teste — sem vazamento de dados entre os conjuntos
- **FR7:** Emili pode configurar o tamanho N da janela deslizante (valores a testar: N=5, N=10, N=20)

### 3. Treinamento e Avaliação de Modelos

- **FR8:** Emili pode treinar um modelo Random Forest sobre os dados de treino
- **FR9:** Emili pode treinar um modelo Decision Tree sobre os dados de treino
- **FR10:** Emili pode treinar um modelo LSTM ou MLP sobre os dados de treino
- **FR11:** O sistema avalia cada modelo com k-fold cross-validation com k configurável (padrão k=5)
- **FR12:** O sistema calcula F1-Score, AUC-ROC, Precision, Recall e FPR para cada modelo
- **FR13:** O sistema reporta métricas com média e desvio padrão entre os folds do k-fold
- **FR14:** O sistema produz tabela comparativa de métricas para todos os modelos avaliados
- **FR15:** Emili pode configurar hiperparâmetros de cada modelo antes do treino

### 4. Rastreamento de Experimentos

- **FR16:** O sistema registra automaticamente parâmetros de cada run (algoritmo, hiperparâmetros, tamanho da janela)
- **FR17:** O sistema registra automaticamente as métricas de avaliação de cada run
- **FR18:** Emili pode comparar resultados de múltiplos runs em painel de rastreamento de experimentos com visualização lado a lado de métricas e parâmetros
- **FR19:** Emili pode exportar resultados dos experimentos em formato CSV para o artigo

### 5. Serialização e Exportação do Modelo

- **FR20:** O sistema serializa o modelo treinado em formato compatível com inferência, incluindo todo o pipeline de pré-processamento necessário, sem dependência do código-fonte de treino
- **FR21:** Emili pode selecionar e exportar o modelo vencedor para uso em produção
- **FR22:** O artefato exportado inclui todo o pipeline de pré-processamento necessário para inferência (scaler, window transformer, encoder)

### 6. Serviço de Predição (API)

- **FR23:** O sistema expõe endpoint HTTP `POST /predict` para receber janela de tráfego e retornar predição
- **FR24:** O endpoint retorna: tipo de ameaça prevista, nível de confiança do modelo e identificador do modelo
- **FR25:** O sistema disponibiliza documentação interativa do endpoint (`GET /docs`)
- **FR26:** O sistema disponibiliza endpoint mock com respostas fixas para desenvolvimento paralelo da interface de Isabela

### 7. Alertas e Visualização (Módulo Isabela)

- **FR27:** O sistema de alertas exibe tipo de ameaça prevista, nível de confiança do modelo, timestamp da janela de tráfego e identificador do modelo que gerou a predição
- **FR28:** O sistema de alertas mantém histórico das últimas ≥ 100 notificações com tipo de ameaça, confiança, timestamp e status (confirmado / descartado pelo analista)
- **FR29:** Analistas podem configurar threshold mínimo de confiança para disparo de alertas e registrar feedback por alerta (confirmar ameaça real ou descartar como falso positivo)

### 8. Reprodutibilidade e Documentação

- **FR30:** O sistema garante resultados reprodutíveis com seed configurável fixo em todos os modelos, produzindo métricas idênticas para a mesma combinação de dados e hiperparâmetros
- **FR31:** O projeto documenta todas as dependências com versões fixadas em arquivo de dependências padrão do ecossistema, garantindo ambiente reprodutível
- **FR32:** O projeto fornece instruções de instalação e execução para reprodução dos experimentos (README)
- **FR33:** O sistema gera relatório de desempenho dos modelos exportável para inclusão no artigo científico

---

## Non-Functional Requirements

### Performance

- **NFR1:** A inferência do modelo via `POST /predict` deve retornar resposta em ≤ 10 segundos para uma janela de tráfego de tamanho N ≤ 20 registros
- **NFR2:** O carregamento do modelo serializado na inicialização da API deve completar em ≤ 5 segundos
- **NFR3:** O treino de RF e DT sobre o CICIDS2017 completo deve completar em ≤ 2 horas em CPU (Intel Core i5 ou equivalente, 8GB RAM)
- **NFR4:** O treino do LSTM deve ser viável em ≤ 4 horas no Google Colab (GPU T4 gratuita)

### Reprodutibilidade Científica

- **NFR5:** Executando o pipeline com os mesmos dados e seed configurável fixo, os resultados das métricas devem ser idênticos em qualquer execução (variação ≤ 0.01%)
- **NFR6:** O ambiente de execução deve ser reconstituível via gerenciador de pacotes padrão a partir do arquivo de dependências, em Python ≥ 3.10, sem conflitos de dependências
- **NFR7:** O README deve permitir que um pesquisador externo reproduza os experimentos principais em ≤ 30 minutos de setup

### Integração

- **NFR8:** O endpoint `POST /predict` deve aceitar e retornar JSON válido conforme schema documentado em `/docs`
- **NFR9:** O pipeline de treino deve aceitar qualquer CSV que respeite o contrato de interface definido com Caroline sem modificação de código
- **NFR10:** O modelo exportado deve ser carregável e utilizável para inferência em ambiente limpo sem acesso ao código-fonte de treino, verificável ao executar predição com sucesso em ambiente de instalação nova contendo apenas o artefato exportado e o arquivo de dependências

### Segurança (Básica)

- **NFR11:** A API deve servir exclusivamente em `localhost` por padrão — não exposta à rede externa sem configuração explícita
- **NFR12:** Nenhum dado pessoal ou sensível de usuários reais é processado — apenas o dataset público CICIDS2017 e dados simulados gerados por Isabela
