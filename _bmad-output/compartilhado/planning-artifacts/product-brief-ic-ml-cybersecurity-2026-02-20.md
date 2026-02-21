---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - "docs/Plano individual - Emili Vieira Tabuti.pdf"
  - "docs/Plano individual de IC - Caroline.docx"
  - "docs/Plano individual-Isabela Groke Gomes.docx"
date: 2026-02-20
author: Emili-tabuti
---

# Product Brief: ic-ml-cybersecurity

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

O projeto "Sistema de Previsão de Ataques Cibernéticos com Machine Learning"
visa desenvolver um sistema capaz de identificar e alertar sobre tentativas de
ataques cibernéticos antes que se concretizem, utilizando algoritmos de Machine
Learning treinados em dados de tráfego de rede. O sistema é destinado
primariamente a pesquisadores de segurança cibernética, tendo redes acadêmicas
como caso de uso inicial. A pesquisa é conduzida por três estudantes de Ciência
da Computação sob orientação do Prof. Dr. Daniel Couto Gatti (FCET), com escopos
complementares cobrindo coleta de dados, implementação de modelos e avaliação
em ambiente simulado.

---

## Core Vision

### Problem Statement

Ferramentas tradicionais de segurança de rede (IDS/IPS como Snort, Suricata) e
sistemas SIEM operam de forma reativa — detectam ataques somente após sua
ocorrência, baseando-se em regras fixas e assinaturas conhecidas. Isso deixa
redes expostas a ataques zero-day e ameaças emergentes, especialmente em
ambientes acadêmicos onde dados sensíveis de pesquisa e informações institucionais
estão em risco.

### Problem Impact

A detecção tardia de ataques cibernéticos resulta em:
- Comprometimento de dados sensíveis antes de qualquer resposta
- Alto custo de remediação pós-ataque
- Incapacidade de resposta proativa por equipes de segurança
- Falta de ferramentas acessíveis para pesquisadores estudarem padrões de ataque

### Why Existing Solutions Fall Short

- **Ferramentas baseadas em regras** (Snort, Suricata): reativas, exigem
  atualização manual constante de assinaturas, não aprendem novos padrões
- **Sistemas SIEM** (Splunk, etc.): caros, complexos, voltados para operações
  corporativas, não adequados para pesquisa científica
- **Abordagens estáticas**: não se adaptam à evolução das técnicas de ataque

### Proposed Solution

Desenvolvimento de um pipeline completo de previsão de ataques cibernéticos
composto por três módulos integrados:

1. **Módulo de Dados** *(Caroline)*: coleta, limpeza, normalização e
   feature selection de dados de tráfego de rede (fontes públicas e/ou
   infraestrutura universitária)
2. **Módulo de ML** *(Emili)*: implementação, treinamento e avaliação
   comparativa de algoritmos (Decision Tree, Random Forest, SVM, Redes Neurais)
   com métricas de precisão, recall, F1-score e AUC-ROC; integração do melhor
   modelo ao sistema de alerta em tempo real
3. **Módulo de Avaliação** *(Isabela)*: ambiente de teste simulado com
   cenários de ataques reais, interfaces de visualização de alertas,
   mecanismos de notificação e relatório final de desempenho

### Key Differentiators

- **Previsão antecipada** vs. detecção reativa: o sistema age antes do ataque
  se concretizar
- **Abordagem comparativa**: avaliação empírica de múltiplos algoritmos para
  identificar o mais adequado ao contexto de segurança de redes
- **Orientado à pesquisa**: arquitetura acessível e documentada, voltada para
  pesquisadores de segurança, não apenas operadores corporativos
- **Pipeline end-to-end**: cobre todo o ciclo — dados brutos → modelo treinado
  → alerta em tempo real → avaliação em ambiente simulado

---

## Target Users

### Primary Users

**Persona: Ana Souza — Analista de Segurança**

- **Contexto:** Analista de segurança em uma universidade ou centro de pesquisa,
  responsável por monitorar e proteger a infraestrutura de rede institucional.
  Pode atuar também como pesquisadora independente avaliando soluções de detecção
  de ameaças.
- **Motivação:** Garantir a integridade da rede sem precisar monitorar dashboards
  continuamente — quer ser notificada apenas quando algo realmente suspeito ocorre.
- **Frustração atual:** Ferramentas existentes (Snort, SIEM) só alertam após o
  ataque já ter ocorrido, gerando sobrecarga de falsos positivos ou detecção tardia.
- **Decisão de adoção:** Autônoma — avalia e adota a ferramenta por conta própria,
  sem depender de aprovação de TI.
- **Sucesso:** Receber um alerta preciso *antes* do ataque se concretizar, com
  informações suficientes para agir preventivamente.

### Secondary Users

**Equipe de TI da Universidade**
- Recebe e age sobre os alertas gerados pelo sistema
- Não opera o sistema diretamente, mas é impactada pela qualidade e relevância
  dos alertas (baixa taxa de falsos positivos é crítica para este perfil)

**Pesquisadores e Estudantes de Segurança**
- Utilizam o sistema como objeto de estudo: reproduzem experimentos, comparam
  algoritmos e validam resultados em ambiente controlado
- Interessados na documentação técnica e nos dados de avaliação produzidos

### User Journey

**Jornada da Ana (Analista de Segurança):**

1. **Configuração inicial:** Ana instala o sistema, configura a fonte de dados
   de rede (captura de tráfego ou dataset público) e seleciona o modelo ML
   previamente treinado e validado.
2. **Operação passiva:** O sistema monitora o tráfego de rede em segundo plano,
   aplicando o modelo para identificar padrões suspeitos. Ana não precisa
   acompanhar ativamente.
3. **Momento de valor (aha!):** Ana recebe um alerta — *antes* do ataque ocorrer
   — com informações sobre o tipo de ameaça detectada, nível de confiança do
   modelo e dados relevantes para tomada de decisão.
4. **Ação:** Com base no alerta, Ana (ou a equipe de TI) toma medidas preventivas:
   bloqueia IP, isola segmento de rede, investiga o tráfego suspeito.
5. **Avaliação contínua:** Ana acompanha métricas do sistema (precisão, falsos
   positivos) pela interface de visualização para avaliar a confiabilidade do
   modelo ao longo do tempo.

---

## Success Metrics

O sucesso do projeto é avaliado em três dimensões: valor para o usuário,
qualidade científica e funcionalidade do sistema.

### Métricas de Sucesso do Usuário

- **Precisão mínima:** ≥ 90% de acertos nos alertas gerados
- **Taxa de falsos positivos:** ≤ 10% (máximo 1 falso alarme a cada 10 alertas)
- **Detecção antecipada:** alerta disparado *antes* da concretização do ataque
- **Cobertura:** sistema capaz de detectar ao menos os tipos de ataques
  definidos nos cenários simulados por Isabela

### Business Objectives

Como projeto de pesquisa acadêmica, os objetivos equivalem às entregas
científicas e institucionais:

1. **Artigo científico** com resultados da comparação de algoritmos de ML
   aplicados à previsão de ataques cibernéticos
2. **Relatório final de IC** documentando todo o pipeline: dados →
   modelos → sistema de alerta → avaliação
3. **Apresentação em seminário** com demonstração do sistema funcional
   detectando ataques simulados

### Key Performance Indicators

| KPI | Meta | Método de Medição |
|---|---|---|
| Precisão do melhor modelo | ≥ 90% | Métrica precision no conjunto de teste |
| Recall do melhor modelo | A definir | Métrica recall no conjunto de teste |
| F1-Score | Maximizar | Média harmônica precisão/recall |
| AUC-ROC | ≥ 0.90 | Curva ROC no conjunto de teste |
| Taxa de falsos positivos | ≤ 10% | FP / (FP + TN) |
| Tempo de resposta do alerta | A definir | Tempo entre detecção e disparo do alerta |
| Algoritmos comparados | ≥ 4 | Decision Tree, Random Forest, SVM, Redes Neurais |
| Detecção em dados simulados ao vivo | ≥ 1 cenário funcional | Testes de integração com Isabela |

---

## MVP Scope

### Core Features

As seguintes entregas compõem o escopo obrigatório desta IC:

**Módulo de Dados (Caroline — meses 1-7):**
- Coleta e pré-processamento de dados de tráfego de rede
- Limpeza, normalização e feature selection
- Definição da arquitetura do sistema de alerta em tempo real

**Módulo de ML (Emili — meses 1-10):**
- Revisão bibliográfica para seleção dos algoritmos mais adequados
  *(algoritmos e métricas a definir após pesquisa — candidatos: Decision Tree,
  Random Forest, SVM, Redes Neurais)*
- Implementação dos algoritmos selecionados (scikit-learn / TensorFlow / Keras)
- Treinamento com dados pré-processados pela Caroline
- Validação cruzada e avaliação comparativa com métricas a definir
  *(candidatas: precisão, recall, F1-score, AUC-ROC)*
- Integração do melhor algoritmo ao sistema de alerta em tempo real

**Módulo de Avaliação (Isabela — meses 8-12):**
- Interface de visualização dos alertas
- Mecanismos de notificação
- Ambiente de teste simulado com cenários de ataques
- Testes unitários e de integração (em conjunto com Emili)
- Relatório final de avaliação de desempenho

### Out of Scope para esta IC

- Deploy em produção na infraestrutura real da universidade
- Suporte a múltiplos tipos de rede além do caso acadêmico
- Interface mobile
- Integração com ferramentas externas de produção (SIEM corporativo, etc.)

### MVP Success Criteria

O MVP é considerado bem-sucedido quando:
1. Ao menos 1 algoritmo atinge ≥ 90% de precisão no conjunto de teste
2. O sistema detecta ao menos 1 tipo de ataque simulado em dados ao vivo (artificiais)
3. Taxa de falsos positivos ≤ 10%
4. Comparação documentada entre os algoritmos implementados
5. Entregas institucionais cumpridas: artigo, relatório final e seminário

### Future Vision

Se a IC evoluir para um projeto maior, funcionalidades desejadas incluem:

- **Explicabilidade do modelo (XAI):** uso de técnicas como SHAP ou LIME para
  mostrar *por que* o modelo classificou um tráfego como ataque — aumenta a
  confiança do analista na decisão do sistema e agrega valor científico
- Suporte a múltiplos tipos de rede e contextos além do acadêmico
- Deploy em ambiente de produção com dados reais
- Retraining automático do modelo com novos dados
