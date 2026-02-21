# Revisão Bibliográfica: Algoritmos de Machine Learning Aplicados à Segurança Cibernética e Métricas de Avaliação

**Autora:** Emili Vieira Tabuti
**Orientador:** Prof. Dr. Daniel Couto Gatti
**Instituição:** FCET — Faculdade de Ciências Exatas e Tecnologia
**Projeto:** Iniciação Científica — Previsão Antecipada de Ataques Cibernéticos com Machine Learning
**Data:** Fevereiro de 2026

---

## Resumo

Esta revisão bibliográfica sistematiza o estado da arte em algoritmos de Machine Learning (ML) aplicados à detecção e previsão de ataques cibernéticos em redes de computadores. Foram analisados 14 trabalhos científicos publicados entre 2017 e 2025 nas bases IEEE Access, ACM Digital Library, Journal of King Saud University e MDPI Information. A revisão identifica os principais algoritmos utilizados na literatura — com destaque para Random Forest, Decision Tree, SVM e redes neurais recorrentes (LSTM/RNN) —, os datasets de referência e as métricas de avaliação adequadas para comparação empírica de modelos. Os resultados embasam a seleção de algoritmos e o protocolo de avaliação do módulo de Machine Learning desta Iniciação Científica.

**Palavras-chave:** Machine Learning; Segurança Cibernética; Detecção de Intrusão; Previsão de Ataques; Random Forest; LSTM; CICIDS2017; Métricas de Avaliação.

---

## 1. Introdução

A segurança de redes de computadores é um campo em constante evolução, impulsionado pelo aumento da sofisticação dos ataques cibernéticos e pela insuficiência das abordagens tradicionais baseadas em assinaturas fixas (BERTOLI et al., 2021). Ferramentas amplamente utilizadas como Snort, Suricata e sistemas SIEM dependem de regras previamente definidas, o que as torna incapazes de detectar ameaças emergentes e ataques zero-day de forma proativa.

O emprego de algoritmos de Machine Learning como mecanismo de detecção — e, mais recentemente, de previsão antecipada — de intrusões representa uma alternativa promissora (ANKALAKI et al., 2025). Diferentemente das abordagens baseadas em regras, modelos de ML aprendem padrões diretamente dos dados de tráfego de rede, permitindo maior generalização e adaptabilidade.

No contexto desta Iniciação Científica, a pesquisadora Emili Vieira Tabuti é responsável pela implementação e comparação empírica de modelos de ML para previsão antecipada de ataques, integrando-se ao trabalho de coleta e pré-processamento de dados (Caroline) e avaliação em ambiente simulado (Isabela). A presente revisão bibliográfica sistematiza a literatura relevante para embasar as escolhas de algoritmos, datasets e métricas de avaliação do projeto.

---

## 2. Metodologia da Revisão

### 2.1 Estratégia de Busca

A revisão foi conduzida com análise integral dos trabalhos selecionados — incluindo *abstract*, metodologia, resultados e conclusões. Foram consultadas as seguintes bases de dados:

- **IEEE Access** (8 trabalhos)
- **ACM Digital Library** (3 trabalhos)
- **Journal of King Saud University – Computer and Information Sciences** (1 trabalho)
- **MDPI Information** (1 trabalho)

**Período de publicação:** 2017 a 2025
**Total de trabalhos analisados:** 14

### 2.2 Critérios de Inclusão

- Trabalhos que aplicam ML à detecção ou previsão de intrusões em redes de computadores
- Trabalhos que reportam métricas de avaliação quantitativas comparáveis
- Trabalhos com metodologia experimental clara e replicável
- *Surveys* e revisões sistemáticas que consolidam resultados de múltiplos experimentos

### 2.3 Critérios de Exclusão

- Trabalhos com foco exclusivo em segurança de aplicações web sem generalização para tráfego de rede
- Trabalhos sem descrição metodológica suficiente para avaliação crítica

---

## 3. Trabalhos Analisados

| ID | Autores | Título Resumido | Ano | Fonte | Tipo |
|---|---|---|---|---|---|
| P1 | CHAKIR et al. | Ensemble Methods vs. ML Tradicional para Detecção de Ataques Web | 2023 | J. King Saud Univ. | Experimental |
| P2 | MUHURI; SHAH; YUAN | NIDS com SVM Semi-supervisionado e Random Forest | 2021 | ACM SE '21 | Experimental |
| P3 | WANG et al. | NIDS Baseado em ML com Autoencoders e Random Forest | 2024 | ACM CTCNet '24 | Experimental |
| P4 | MAHMUD; HASAN | Revisão de ML para Detecção Adaptativa de Intrusões | 2024 | ACM ICCA '24 | Revisão |
| P5 | YIN et al. | Abordagem de Deep Learning para IDS com RNNs | 2017 | IEEE Access | Experimental |
| P6 | ENNAJI et al. | Desafios Adversariais em NIDS | 2025 | IEEE Access | Survey |
| P7 | BERTOLI et al. | Framework End-to-End para NIDS Baseado em ML (AB-TRAP) | 2021 | IEEE Access | Experimental |
| P8 | AZAM; ISLAM; HUDA | Análise Comparativa de IDS com Decision Tree | 2023 | IEEE Access | Revisão |
| P9 | ANKALAKI et al. | Previsão de Ataques Cibernéticos: do ML Tradicional à IA Generativa | 2025 | IEEE Access | Survey |
| P10 | TRAN et al. | Curadoria e Qualidade de Dados para IDS Baseado em ML | 2022 | IEEE Access | Experimental |
| P11 | ZOU et al. | HC-DTTSVM: NIDS com Decision Tree e Twin SVM | 2023 | IEEE Access | Experimental |
| P12 | BERMAN et al. | Survey de Métodos de Deep Learning para Cibersegurança | 2019 | MDPI Information | Survey |
| P13 | HALBOUNI et al. | ML e Deep Learning para Cibersegurança: Uma Revisão | 2022 | IEEE Access | Revisão |
| P14 | LE JEUNE; GOEDEMÉ; MENTENS | ML para NIDS: Framework Unificado de Avaliação | 2021 | IEEE Access | Experimental |

---

## 4. Algoritmos de Machine Learning na Literatura

### 4.1 Algoritmos de ML Tradicional

#### 4.1.1 Random Forest (RF)

O Random Forest é o algoritmo mais recorrente nos trabalhos analisados, aparecendo em seis dos quatorze estudos (P1, P2, P3, P4, P7, P11). Trata-se de um método *ensemble* baseado em bagging de Árvores de Decisão, que reduz a variância do modelo sem incorrer em custo computacional proibitivo para inferência.

Os resultados reportados na literatura são consistentemente elevados:

| Trabalho | Dataset | Accuracy | F1-Score | AUC-ROC |
|---|---|---|---|---|
| P1 (CHAKIR et al., 2023) | ECML/PKDD 2007 + CSIC HTTP 2010 | 99,597% | 99,129% | 100% |
| P3 (WANG et al., 2024) | CICIDS2017 | 99,02% | 98,85% | — |
| P4 (MAHMUD; HASAN, 2024) | UNSW-NB15 | 95,10% | 95,10% | — |
| P7 (BERTOLI et al., 2021) | LAN + Internet | — | 0,95 | 0,95 |

P1 demonstra que o RF supera consistentemente outras abordagens *ensemble* (boosting, stacking, max voting) e classificadores individuais nos datasets avaliados. P4 confirma o RF como o melhor modelo entre seis alternativas testadas no UNSW-NB15.

#### 4.1.2 Decision Tree (DT)

Presente em cinco trabalhos (P1, P5, P7, P8, P11), a Árvore de Decisão destaca-se pela interpretabilidade e baixo custo computacional. P7 (BERTOLI et al., 2021) — único trabalho brasileiro da seleção, desenvolvido pelo ITA/UFMG em parceria com o Exército Brasileiro — selecionou o DT como algoritmo final para o ambiente LAN por apresentar F1=0,96 e AUC-ROC=0,99 com custo computacional mínimo (kernel-space). Essa característica é relevante para cenários de implantação em produção com recursos limitados.

#### 4.1.3 Support Vector Machine (SVM)

O SVM é avaliado em quatro trabalhos (P1, P2, P5, P11). P2 demonstra que o SVM semi-supervisionado atinge 100% de acurácia em classificação binária no NSL-KDD, mas desempenho inferior ao RF em classificação multiclasse (67,5% vs. 82,4%). P1 reporta que variantes com bagging apresentam tempo de treinamento proibitivo, limitando sua aplicabilidade em pipelines de produção.

#### 4.1.4 Outros Algoritmos

**KNN (K-Nearest Neighbours):** utilizado como *baseline* em P1, P4 e P7; desempenho consistentemente inferior ao RF. **Logistic Regression:** menor desempenho entre os algoritmos avaliados em P4 (accuracy=80,4%, F1=0,791 no UNSW-NB15). **Naïve Bayes:** adequado apenas para dados de baixa dimensionalidade; utilizado como referência em P1, P5 e P8.

### 4.2 Algoritmos de Deep Learning

#### 4.2.1 RNN e LSTM

Redes Neurais Recorrentes (RNN) e sua variante Long Short-Term Memory (LSTM) são os modelos de Deep Learning mais relevantes para a presente pesquisa, dado o caráter temporal dos dados de tráfego de rede. P5 (YIN et al., 2017) demonstra que o modelo RNN-IDS supera J48, ANN, RF e SVM em classificação binária e multiclasse no NSL-KDD, atingindo *detection rate* de 99,81% no conjunto de treinamento e 83,28% no conjunto de teste. P4 reporta LSTM com F1=0,945 no UNSW-NB15, competitivo com o RF.

P12 (BERMAN et al., 2019), do Johns Hopkins University Applied Physics Laboratory, identifica as RNNs como os modelos de Deep Learning mais populares para cibersegurança, justamente por sua capacidade de modelar dependências temporais em fluxos de tráfego.

#### 4.2.2 MLP (Multi-Layer Perceptron)

O MLP é avaliado em P4 e P5. Em P4, atinge accuracy ~93,1% e F1=0,931 no UNSW-NB15 — desempenho competitivo com o LSTM e superior à Logistic Regression, porém inferior ao RF em accuracy.

#### 4.2.3 Autoencoders

P3 emprega *Stacked Autoencoders* (SAE) como extratores de features antes do Random Forest, atingindo accuracy=98,5% e precision/recall > 97% no CICIDS2017. P12 destaca autoencoders como populares para cenários com dados não rotulados, tornando-os adequados para detecção de anomalias.

#### 4.2.4 CNN, DBN e Modelos de Linguagem

CNNs são empregadas para tráfego tratado como sequência ou imagem (P12, P13). DBNs com pré-treinamento não supervisionado (P12) superam ANN e SVM em benchmarks clássicos. P10 demonstra que modelos de linguagem (BERT, GPT-2) superam todos os oito classificadores ML clássicos testados em datasets *host-based*, sendo mais robustos a dados duplicados e sobrepostos.

### 4.3 Métodos Ensemble

P1 (CHAKIR et al., 2023) conduz o único estudo da seleção dedicado exclusivamente à comparação entre abordagens *ensemble*, com os seguintes resultados:

| Método | Accuracy | Observação |
|---|---|---|
| **Random Forest (bagging)** | **99,597%** | Mais consistente em todas as métricas |
| Boosting | < RF | Recall e FNR inferiores |
| Max Voting (heterogêneo) | < RF | — |
| Stacking (com SVM) | Inferior a classificadores únicos | Tempo de treino > 1700s — inviável em produção |

> **Conclusão de P1:** Métodos *ensemble* não superam consistentemente classificadores individuais. O stacking com SVM é inviável para uso operacional pelo tempo de treinamento.

---

## 5. Datasets de Referência

| Dataset | Ano | Características | Avaliação |
|---|---|---|---|
| **CICIDS2017** | 2017 | Canadian Institute for Cybersecurity. 15+ tipos de ataque. Tráfego de fundo realista. DDoS, Botnet, Brute Force, Infiltration. | ✅ **Recomendado — principal** |
| **NSL-KDD** | 2009 | Versão aprimorada do KDD'99, sem registros redundantes. 4 categorias de ataque. Benchmark clássico da literatura. | ✅ Recomendado — comparativo |
| **UNSW-NB15** | 2015 | Gerado pelo ACCS (Austrália). Tráfego real + sintético. 9 tipos de ataque. Mais desafiador que NSL-KDD. | ✅ Recomendado — complementar |
| **KDD Cup '99** | 1999 | Primeiro grande benchmark. **78% dos registros são duplicados** (LE JEUNE et al., 2021). Considerado obsoleto. | ❌ **Não utilizar** |

P14 (KU Leuven) demonstra que a utilização do KDD'99 infla artificialmente as métricas de desempenho devido à alta proporção de duplicatas, tornando os resultados não comparáveis com estudos que utilizam datasets mais modernos.

---

## 6. Métricas de Avaliação

### 6.1 Métricas Identificadas na Literatura

| Métrica | Fórmula | Utilizada em | Observação |
|---|---|---|---|
| **F1-Score** | 2 × (Precision × Recall) / (Precision + Recall) | P2, P3, P4, P7, P11, P14 | **Métrica principal recomendada** — equilibra precisão e revocação |
| **AUC-ROC** | Área sob a curva ROC | P1, P7, P14 | Avalia separabilidade independentemente do limiar de decisão |
| **Precision** | TP / (TP + FP) | P1, P3, P7, P11, P13 | Proporção de alertas corretos — relevante para carga operacional |
| **Recall (Detection Rate)** | TP / (TP + FN) | P1, P3, P7, P11, P13 | Proporção de ataques detectados — crítico para segurança |
| **False Positive Rate (FPR)** | FP / (FP + TN) | P1, P7, P11 | Alertas falsos recebidos pelo analista |
| **False Negative Rate (FNR)** | FN / (FN + TP) | P1, P14 | Ataques não detectados — risco de segurança direto |
| **Accuracy** | (TP + TN) / Total | P1, P2, P3, P4, P5, P7, P11 | Insuficiente isoladamente em datasets desbalanceados |
| **G-mean** | √(Recall × Specificity) | P11 | Útil para datasets desbalanceados |

### 6.2 Limitações do Uso Isolado de Accuracy

P14 (LE JEUNE et al., 2021) demonstra empiricamente que a *accuracy* isolada é uma métrica inadequada para avaliação de sistemas de detecção de intrusão em datasets desbalanceados — condição típica, uma vez que tráfego malicioso representa uma fração minoritária do tráfego total. Um classificador que prevê toda instância como normal pode atingir *accuracy* superior a 95% mesmo sem detectar nenhum ataque.

### 6.3 Protocolo de Avaliação Recomendado pela Literatura

P14 propõe um framework unificado de avaliação para possibilitar comparação justa entre estudos. As recomendações convergentes da literatura indicam:

1. **Reportar F1-Score como métrica primária** — equilibra Precision e Recall, comparável entre estudos
2. **Incluir AUC-ROC** — avalia desempenho independentemente do limiar de decisão
3. **Reportar FPR** — informa sobre carga operacional ao analista (falsos alarmes)
4. **Utilizar k-fold cross-validation** — valida robustez e evita overfitting (P5, P7)
5. **Avaliar em conjuntos de treino e teste separados** — P5 demonstra degradação de 99,81% → 83,28% ao mudar do conjunto de treino para o conjunto de teste no NSL-KDD

---

## 7. Temas Emergentes e Limitações da Literatura

### 7.1 Ataques Adversariais

P6 (ENNAJI et al., 2025) demonstra que modelos ML para detecção de intrusão são vulneráveis a ataques adversariais do tipo *evasion*: um adversário com conhecimento do modelo pode manipular o tráfego malicioso para que seja classificado como normal. Esta é uma limitação estrutural relevante a ser discutida no artigo científico desta IC.

### 7.2 Explicabilidade (XAI)

P1 e P9 identificam a explicabilidade como desafio em aberto na literatura de ML para segurança. Ferramentas como SHAP, LIME e Grad-CAM permitem interpretação post-hoc de modelos caixa-preta (RF, redes neurais). Decision Tree e Logistic Regression são modelos inerentemente interpretáveis, o que representa vantagem operacional em contextos que exigem auditoria.

### 7.3 Qualidade de Dados

P10 (TRAN et al., 2022) demonstra que dados duplicados degradam modelos ML clássicos de forma mais pronunciada do que modelos de linguagem. As dimensões críticas de qualidade identificadas são: relevância, abrangência, consistência, ausência de duplicação e ausência de sobreposição entre conjuntos de treino e teste.

### 7.4 Diferencial deste Trabalho em Relação à Literatura

Os 14 trabalhos analisados focam predominantemente em **detecção** — classificação de tráfego em andamento — como problema de classificação estática. Esta IC aplica a abordagem de **previsão antecipada** com sliding window temporal, modelando o problema como série temporal. Esta distinção posiciona o trabalho em um recorte menos explorado da literatura, com maior valor operacional para analistas de segurança.

---

## 8. Síntese e Justificativa para a IC

### 8.1 Algoritmos Selecionados

Com base na análise sistemática da literatura, os seguintes algoritmos foram selecionados para implementação e comparação empírica nesta IC:

| Algoritmo | Justificativa Bibliográfica |
|---|---|
| **Random Forest** | Melhor desempenho geral em 5 dos 14 papers analisados. F1 e AUC-ROC consistentemente superiores. Amplamente adotado como referência na literatura (P1, P2, P3, P4, P7). |
| **Decision Tree** | Interpretabilidade e eficiência computacional comprovadas. P7 (paper brasileiro) selecionou DT em ambiente de produção pela relação custo-benefício (F1=0,96, AUC=0,99). |
| **LSTM / RNN** | Representação do paradigma de Deep Learning com capacidade de modelagem temporal. P5: RNN-IDS supera todos os classificadores ML clássicos em NSL-KDD. P12: método DL mais popular para dados de tráfego de rede. |
| **SVM** | Referência clássica bem documentada. Permite comparação direta com a literatura consolidada (P1, P2, P5). |

### 8.2 Dataset Principal

**CICIDS2017** como dataset principal, por ser o mais atual e representativo do tráfego moderno. **NSL-KDD** como comparativo de baseline para facilitar comparação com a literatura clássica. **KDD Cup '99** descartado em razão da alta proporção de duplicatas identificada por P14.

### 8.3 Protocolo de Métricas

Métricas obrigatórias a reportar: **F1-Score, AUC-ROC, Precision, Recall e FPR**.
Métricas complementares: Accuracy e tempo de treinamento/predição.
Validação: k-fold cross-validation (k=5) com separação estrita de conjuntos de treino e teste.

---

## Referências

ANKALAKI, S. et al. Cyber Attack Prediction: From Traditional Machine Learning to Generative Artificial Intelligence. **IEEE Access**, v. 13, 2025.

AZAM, Z.; ISLAM, M. M.; HUDA, M. N. Comparative Analysis of Intrusion Detection Systems and Machine Learning-Based Model Analysis Through Decision Tree. **IEEE Access**, v. 11, 2023.

BERMAN, D. S. et al. A Survey of Deep Learning Methods for Cyber Security. **Information**, v. 10, n. 4, p. 122, 2019.

BERTOLI, G. C. et al. An End-to-End Framework for Machine Learning-Based Network Intrusion Detection System. **IEEE Access**, v. 9, 2021.

CHAKIR, O. et al. An empirical assessment of ensemble methods and traditional machine learning techniques for web-based attack detection in industry 5.0. **Journal of King Saud University – Computer and Information Sciences**, v. 35, p. 103–119, 2023.

ENNAJI, S. et al. Adversarial Challenges in Network Intrusion Detection Systems: Research Insights and Future Prospects. **IEEE Access**, v. 13, 2025.

HALBOUNI, A. et al. Machine Learning and Deep Learning Approaches for CyberSecurity: A Review. **IEEE Access**, v. 10, 2022.

LE JEUNE, L.; GOEDEMÉ, T.; MENTENS, N. Machine Learning for Misuse-Based Network Intrusion Detection: Overview, Unified Evaluation and Feature Choice Comparison Framework. **IEEE Access**, v. 9, 2021.

MAHMUD, M. A.; HASAN, K. T. Advancements in Machine Learning for Adaptive Intrusion Detection: A Comprehensive Review. **ICCA 2024**, 2024.

MUHURI, P. S.; SHAH, S.; YUAN, X. Implementing a network intrusion detection system using semi-supervised support vector machine and random forest. **ACM Southeast Conference (ACM SE '21)**, 2021.

TRAN, N. et al. Data Curation and Quality Evaluation for Machine Learning-Based Cyber Intrusion Detection. **IEEE Access**, v. 10, 2022.

WANG, P. et al. Design and Implementation of a Machine Learning-Based Network Intrusion Detection System. **ACM CTCNet 2024**, 2024.

YIN, C. et al. A Deep Learning Approach for Intrusion Detection Using Recurrent Neural Networks. **IEEE Access**, v. 5, p. 21954–21961, 2017.

ZOU, L. et al. HC-DTTSVM: A Network Intrusion Detection Method Based on Decision Tree Twin Support Vector Machine and Hierarchical Clustering. **IEEE Access**, v. 11, 2023.
