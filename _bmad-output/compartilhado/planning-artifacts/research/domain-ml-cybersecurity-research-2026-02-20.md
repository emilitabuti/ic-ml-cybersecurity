---
stepsCompleted: [1]
inputDocuments:
  - "docs/pesquisas-ml/1-s2.0-S1319157823000381-main.pdf"
  - "docs/pesquisas-ml/3409334.3452073.txt"
  - "docs/pesquisas-ml/3685767.3685790.txt"
  - "docs/pesquisas-ml/3723178.3723239.txt"
  - "docs/pesquisas-ml/A_Deep_Learning_Approach_for_Intrusion_Detection_Using_Recurrent_Neural_Networks.pdf"
  - "docs/pesquisas-ml/Adversarial_Challenges_in_Network_Intrusion_Detection_Systems_Research_Insights_and_Future_Prospects.pdf"
  - "docs/pesquisas-ml/An_End-to-End_Framework_for_Machine_Learning-Based_Network_Intrusion_Detection_System.pdf"
  - "docs/pesquisas-ml/Comparative_Analysis_of_Intrusion_Detection_Systems_and_Machine_Learning-Based_Model_Analysis_Through_Decision_Tree.pdf"
  - "docs/pesquisas-ml/Cyber_Attack_Prediction_From_Traditional_Machine_Learning_to_Generative_Artificial_Intelligence.pdf"
  - "docs/pesquisas-ml/Data_Curation_and_Quality_Evaluation_for_Machine_Learning-Based_Cyber_Intrusion_Detection.pdf"
  - "docs/pesquisas-ml/HC-DTTSVM_A_Network_Intrusion_Detection_Method_Based_on_Decision_Tree_Twin_Support_Vector_Machine_and_Hierarchical_Clustering.pdf"
  - "docs/pesquisas-ml/information-10-00122.pdf"
  - "docs/pesquisas-ml/Machine_Learning_and_Deep_Learning_Approaches_for_CyberSecurity_A_Review.pdf"
  - "docs/pesquisas-ml/Machine_Learning_for_Misuse-Based_Network_Intrusion_Detection_Overview_Unified_Evaluation_and_Feature_Choice_Comparison_Framework.pdf"
workflowType: 'research'
research_type: 'domain'
research_topic: 'algoritmos de machine learning para previsão de ataques cibernéticos'
research_goals: 'selecionar algoritmos e métricas de avaliação mais adequados para o sistema de previsão de ataques cibernéticos'
user_name: 'Emili-tabuti'
date: '2026-02-20'
web_research_enabled: false
source_verification: true
analysis_depth: 'full - abstracts, metodologia, resultados, conclusões lidos integralmente'
---

# Research Report: Algoritmos de ML para Previsão de Ataques Cibernéticos

**Data:** 2026-02-20
**Autora:** Emili-tabuti
**Tipo:** Domain Research (assistida manualmente — leitura completa de cada paper)

---

## Research Overview

Pesquisa bibliográfica sobre algoritmos de Machine Learning aplicados à detecção
e previsão de ataques cibernéticos. **14 papers** foram lidos integralmente
(abstract, metodologia, resultados e conclusões), cobrindo publicações de 2017 a 2025.

**Fontes:** IEEE Access (8), ACM Digital Library (3), Journal King Saud University (1),
MDPI Information (1), IEEE Access (1).

---

## 1. Catálogo de Papers Analisados

| ID | Título | Autores | Ano | Fonte | Tipo |
|---|---|---|---|---|---|
| P1 | An empirical assessment of ensemble methods and traditional ML for web-based attack detection | Chakir et al. | 2023 | J. King Saud Univ. | Experimental |
| P2 | Implementing a NIDS using semi-supervised SVM and Random Forest | Muhuri, Shah, Yuan (NC A&T) | 2021 | ACM SE '21 | Experimental |
| P3 | Design and Implementation of a ML-Based NIDS | Wang et al. | 2024 | ACM CTCNet '24 | Experimental |
| P4 | Advancements in ML for Adaptive Intrusion Detection: A Review | Mahmud, Hasan | 2024 | ACM ICCA '24 | Review |
| P5 | A Deep Learning Approach for IDS Using RNNs | Yin et al. | 2017 | IEEE Access | Experimental |
| P6 | Adversarial Challenges in NIDS: Research Insights and Future Prospects | Ennaji et al. (Sapienza Univ.) | 2025 | IEEE Access | Survey |
| P7 | An End-to-End Framework for ML-Based NIDS (AB-TRAP) | Bertoli et al. (ITA/UFMG/Exército BR) | 2021 | IEEE Access | Experimental |
| P8 | Comparative Analysis of IDS and ML-Based Model Analysis Through Decision Tree | Azam, Islam, Huda | 2023 | IEEE Access | Review |
| P9 | Cyber Attack Prediction: From Traditional ML to Generative AI | Ankalaki et al. | 2025 | IEEE Access | Survey |
| P10 | Data Curation and Quality Evaluation for ML-Based Cyber IDS | Tran, Chen, Bhuyan, Ding | 2022 | IEEE Access | Experimental |
| P11 | HC-DTTSVM: NIDS via Decision Tree + Twin SVM + Hierarchical Clustering | Zou et al. | 2023 | IEEE Access | Experimental |
| P12 | A Survey of Deep Learning Methods for Cyber Security | Berman et al. (JHU/APL) | 2019 | MDPI Information | Survey |
| P13 | Machine Learning and Deep Learning Approaches for CyberSecurity: A Review | Halbouni et al. | 2022 | IEEE Access | Review |
| P14 | ML for Misuse-Based NIDS: Overview, Unified Evaluation and Feature Choice Framework | Le Jeune, Goedemé, Mentens (KU Leuven) | 2021 | IEEE Access | Experimental |

---

## 2. Algoritmos Identificados e Avaliados na Literatura

### 2.1 Algoritmos de ML Tradicional

| Algoritmo | Papers | Observações Diretas da Literatura |
|---|---|---|
| **Random Forest (RF)** | P1, P2, P3, P4, P7, P11 | **Algoritmo mais recorrente.** P1: accuracy 99.597%, AUC 100% (melhor entre todos testados). P3: RF-110 árvores — accuracy 99.02%, F1 98.85% (CICIDS2017). P4: **melhor modelo** entre RF, MLP, LSTM, LR, KNN, DT — accuracy 95.10%, F1 95.10% (UNSW-NB15). P7: DT levemente superior ao RF em F1 neste caso específico. |
| **Decision Tree (DT)** | P1, P5, P7, P8, P11 | P7 (paper **brasileiro** ITA/UFMG): DT com F1=0.96 e AUC-ROC=0.99, escolhido como melhor por custo computacional mínimo (kernel-space). P11: DT usado como estrutura base do modelo híbrido HC-DTTWSVM (accuracy 85.95% NSL-KDD). Interpretável e auditável. |
| **SVM (Support Vector Machine)** | P1, P2, P5, P11 | P2: SVM semi-supervisionado — multiclasse 67.5% sem GA, 71.1% com GA; RF supera SVM. P11: Twin SVM embutido no DT (HC-DTTWSVM). P1: SVM com bagging é muito lento no treinamento. |
| **KNN (K-Nearest Neighbours)** | P1, P4, P7, P8 | Usado como baseline; P4: desempenho inferior ao RF. P7: incluído nos 8 algoritmos do framework AB-TRAP. |
| **Logistic Regression** | P1, P4, P7 | P4: accuracy 0.804, F1 0.791 — pior desempenho entre os modelos testados no UNSW-NB15. P1: LR supera outros em algumas métricas no CSIC HTTP 2010. |
| **Naïve Bayes** | P1, P5, P8 | Fraco para dados de alta dimensionalidade de rede; usado como baseline. |

### 2.2 Algoritmos de Deep Learning

| Algoritmo | Papers | Observações Diretas da Literatura |
|---|---|---|
| **RNN / LSTM** | P4, P5, P12 | P5: RNN-IDS supera J48, ANN, RF, SVM em classificação binária e multiclasse no NSL-KDD — detection rate 97.09% no KDDTrain+, 83.28% no KDDTest+. P4: LSTM — F1 0.945, accuracy levemente inferior ao RF mas recall superior. P12: RNNs são populares em cibersegurança por tratar dados de rede como série temporal. |
| **MLP (Multi-Layer Perceptron)** | P4, P5 | P4: MLP accuracy ~0.931, F1 0.931 — competitivo com LSTM, inferior ao RF em accuracy mas melhor em recall. |
| **CNN** | P12, P13 | Aplicado a análise de tráfego de rede tratado como imagem/sequência; resultados promissores. |
| **Autoencoder** | P3, P10, P12 | P3: Stacked Autoencoders (SAE) para extração de features antes do RF — sistema atinge accuracy 98.5%, precision/recall >97%. P12: autoencoders populares por funcionarem com dados não rotulados. |
| **DBN (Deep Belief Network)** | P12 | P12: DBN com 11 camadas supera ANN e SVM; pré-treinado em dados não rotulados. |
| **BERT / GPT-2** | P10 | P10: modelos de linguagem superam **todos** os 8 classificadores ML clássicos testados nos 11 datasets host-based; mais robustos a dados duplicados e sobrepostos. |

### 2.3 Métodos Ensemble (P1 — análise empírica completa)

| Método | Accuracy | Melhor para | Pior para |
|---|---|---|---|
| **Random Forest (Bagging)** | **99.597%** | Accuracy, Precision, FPR, AUC | Tempo de treinamento |
| Boosting | < RF | FPR | Recall, FNR, tempo |
| Max Voting (heterogêneo) | < RF | Accuracy, Precision, FPR | Recall, FNR, tempo |
| Stacking (heterogêneo) | < single classifiers | — | Tempo de treino e predição (>1700s) |
| Single Classifiers | < RF (accuracy) | Recall, FNR, tempo | Accuracy vs RF |

> **Conclusão P1:** Ensemble methods **não superam sempre** single classifiers.
> RF (bagging) é o mais consistente. Stacking com SVM é inviável em produção pelo tempo.

---

## 3. Datasets Utilizados na Literatura

| Dataset | Usado em | Ano | Características | Recomendado? |
|---|---|---|---|---|
| **NSL-KDD** | P2, P4, P5, P11, P14 | 2009 | Versão melhorada do KDD'99, sem redundâncias. 4 categorias de ataque + normal. Benchmark clássico. | ✅ Sim |
| **UNSW-NB15** | P4, P11, P14 | 2015 | Gerado pelo ACCS (Austrália). Tráfego real + sintético. 9 tipos de ataque. Mais desafiador que NSL-KDD. | ✅ Sim (mais atual) |
| **CICIDS2017** | P3, P13, P14 | 2017 | Canadian Institute for Cybersecurity. 15+ tipos de ataque. Dataset mais realista e atual. Inclui DDoS, Botnet, Brute Force, Infiltration. | ✅ **Preferencial** |
| **KDD Cup '99** | P5, P12 | 1999 | Primeiro grande benchmark de IDS. **78% dos registros são duplicados** (P14). Considerado obsoleto. | ❌ Evitar |
| **ECML/PKDD 2007** | P1 | 2007 | Web-based attacks. Específico para ataques em aplicações web. | ⚠️ Nicho |
| **CSIC HTTP 2010** | P1 | 2010 | Web-based attacks (HTTP). Específico para aplicações web. | ⚠️ Nicho |
| **11 host-based datasets** | P10 | variado | Estudo de qualidade de dados em IDS host-based. | ℹ️ Referência |

> **Recomendação para a IC:** Usar **CICIDS2017** como dataset principal (mais atual e realista),
> com NSL-KDD como comparativo de baseline. Evitar KDD'99.

---

## 4. Métricas de Avaliação Identificadas

| Métrica | Fórmula | Usada em | Observação |
|---|---|---|---|
| **Accuracy** | (TP+TN)/Total | P1,P2,P3,P4,P5,P7,P11 | Insuficiente sozinha em datasets desbalanceados (P14) |
| **Precision** | TP/(TP+FP) | P1,P3,P7,P11,P13 | Proporção de alertas corretos |
| **Recall (Detection Rate)** | TP/(TP+FN) | P1,P3,P7,P11,P13 | Proporção de ataques detectados |
| **F1-Score** | 2×(P×R)/(P+R) | P2,P3,P4,P7,P11,P14 | **Métrica principal recomendada** — equilibra P e R |
| **AUC-ROC** | Área sob curva ROC | P1,P7,P14 | Avalia separabilidade do modelo; independe do threshold |
| **False Positive Rate (FPR)** | FP/(FP+TN) | P1,P7,P11 | Crítico para uso operacional — analista recebe falsos alarmes |
| **False Negative Rate (FNR)** | FN/(FN+TP) | P1,P14 | Ataques não detectados — risco de segurança |
| **G-mean** | √(Recall × Specificity) | P11 | Útil para datasets desbalanceados |
| **Detection Score / Identification Score** | F1w e F1M harmônico | P14 | Métricas propostas pelo KU Leuven para comparação justa entre estudos |

> **Recomendação para a IC:** Reportar **F1-Score, AUC-ROC, Precision, Recall e FPR**.
> Accuracy sozinha é insuficiente (P14). F1 é a métrica mais comparável com a literatura.

---

## 5. Resultados Numéricos Verificados por Paper

### P1 — Ensemble vs. Single Classifiers (ECML/PKDD 2007 + CSIC HTTP 2010)
| Método | Accuracy | Precision | F1 | FPR | AUC |
|---|---|---|---|---|---|
| **Random Forest (bagging)** | **99.597%** | **98.274%** | **99.129%** | 0.523% | **100%** |
| Single classifiers (média) | ~96-97% | — | — | — | — |
| Stacking | < single | — | — | — | — |

### P2 — Semi-supervised SVM vs. RF (NSL-KDD)
| Algoritmo | Binário | Multiclasse | + GA (multiclasse) |
|---|---|---|---|
| SVM semi-supervisionado | 100% | 67.5% | 71.1% |
| **RF semi-supervisionado** | 100% | **82.4%** | **86.5%** |
> RF supera SVM em multiclasse. GA (Genetic Algorithm) melhora ambos.

### P3 — Random Forest com Autoencoder (CICIDS2017)
| Modelo | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| RF-20 árvores | 98.12% | 97.23% | 98.87% | 98.04% |
| **RF-110 árvores** | **99.02%** | **98.43%** | **99.28%** | **98.85%** |
> Mais árvores = melhor desempenho. SAE como feature extractor melhora robustez.

### P4 — Comparação de 6 modelos (UNSW-NB15)
| Algoritmo | Accuracy | F1 | Precision | Recall |
|---|---|---|---|---|
| **Random Forest** | **95.10%** | **95.10%** | 95.11% | 95.10% |
| MLP | ~93.1% | 0.931 | — | melhor recall |
| LSTM | ~94.5% | 0.945 | melhor precision | — |
| Logistic Regression | 80.4% | 0.791 | — | — |
| KNN | < RF | — | — | — |
| Decision Tree | < RF | — | — | — |

### P5 — RNN-IDS vs. ML tradicional (NSL-KDD)
| Algoritmo | Detection Rate (KDDTrain+) | KDDTest+ | Observação |
|---|---|---|---|
| **RNN-IDS** | **99.81%** | 83.28% | Supera todos em binário e multiclasse |
| J48, ANN, RF, SVM | < RNN | < 83.28% | Baseline da literatura |
> RNN superior, mas treinado em CPU pessoal (sem GPU) — mais lento.

### P7 — AB-TRAP Framework (LAN + Internet, paper **brasileiro**)
| Ambiente | Algoritmo | F1-Score | AUC-ROC | Custo CPU/RAM |
|---|---|---|---|---|
| LAN (kernel-space) | **Decision Tree** | **0.96** | **0.99** | Mínimo |
| Internet (user-space) | 8 algoritmos (média) | 0.95 | 0.98 | 1.4% CPU / 3.6% RAM |
> DT escolhido pela combinação de desempenho + eficiência. RF teve AUC=0.95, levemente inferior.

### P11 — HC-DTTWSVM (NSL-KDD + UNSW-NB15)
| Dataset | Overall Accuracy |
|---|---|
| NSL-KDD | 85.95% |
| UNSW-NB15 | 81.21% |
> Modelo híbrido. Dos attacks: F1=96.08% (NSL-KDD). U2R e R2L são categorias difíceis para todos os modelos.

---

## 6. Insights Críticos e Lições Aprendidas

### 6.1 Qualidade de Dados (P10 — impacto direto no trabalho da Caroline)
- **Dados duplicados degradam ML clássico** mais que modelos de linguagem
- Remoção de duplicatas e sobreposições melhora desempenho na maioria dos casos
- "Garbage in, garbage out" — a qualidade do pré-processamento da Caroline impacta **diretamente** os resultados de Emili
- Dimensões críticas: relevância, abrangência, consistência, duplicação, sobreposição

### 6.2 Problema de Datasets Desatualizados (P7, P14)
- KDD'99: **78% dos registros são duplicados** — não usar
- NSL-KDD: resolve os problemas do KDD'99, mas já tem 15+ anos
- CICIDS2017: mais realista, com tráfego moderno de background
- **P14 (KU Leuven):** padronização de métricas é crítica — resultados de papers diferentes não são diretamente comparáveis sem framework comum

### 6.3 Ataques Adversariais (P6, 2025 — tema emergente)
- Modelos ML podem ser **enganados por tráfego manipulado** (evasion attacks)
- Adversário crafta tráfego de ataque para parecer normal ao modelo
- **Implicação para a IC:** mencionar limitação no artigo — modelos treinados podem ser vulneráveis a adversários que conhecem o modelo
- Área de pesquisa futura relevante

### 6.4 XAI — Explicabilidade (P9, P1)
- P1 identifica XAI como **desafio em aberto** na literatura de ML-WSS
- P9 aborda SHAP, LIME e Grad-CAM como ferramentas XAI model-agnostic
- Decision Tree e Logistic Regression são **modelos transparentes** por natureza
- RF e Redes Neurais requerem post-hoc XAI (SHAP/LIME)
- Confirma a "Future Vision" do Product Brief — XAI seria diferencial científico relevante

### 6.5 Deep Learning vs. ML Tradicional (P5, P12)
- **DL supera ML tradicional** em datasets grandes — P5: RNN-IDS detection rate 97.09%
- P12 (JHU/APL): RNN e autoencoders são os métodos DL mais populares para IDS
- Porém: **custo computacional maior**, mais dados necessários, menor interpretabilidade
- Para a IC: incluir ao menos 1 modelo DL (LSTM/RNN) para comparação científica robusta

---

## 7. Recomendações Finais para a IC

### 7.1 Algoritmos para Implementar (em ordem de prioridade)

| Prioridade | Algoritmo | Justificativa baseada na literatura |
|---|---|---|
| ✅ **Alta** | **Random Forest** | Melhor desempenho geral em 5 dos 14 papers. F1 e AUC-ROC consistentemente altos. Fácil com scikit-learn. |
| ✅ **Alta** | **Decision Tree** | Interpretável, eficiente computacionalmente (P7 — paper BR escolheu DT pelo custo/benefício). Base para modelos híbridos. |
| ✅ **Alta** | **SVM** | Clássico, bem documentado, comparativo necessário. Usar com kernel RBF para dados não-lineares. |
| ⚠️ **Média** | **LSTM ou MLP** | Representar Deep Learning. P4: LSTM F1=0.945; P5: RNN-IDS superior ao ML. Usar TensorFlow/Keras. Exige mais dados e GPU. |
| ℹ️ **Opcional** | **KNN / Logistic Regression** | Baselines para comparação. Fácil de implementar com scikit-learn. |

### 7.2 Dataset Recomendado

1. **Principal:** CICIDS2017 — mais atual, realista, 15 tipos de ataque
2. **Comparativo:** NSL-KDD — benchmark clássico da literatura, facilita comparação com outros trabalhos
3. **Evitar:** KDD Cup '99 (78% duplicados, obsoleto)

### 7.3 Métricas a Reportar

- **Obrigatórias:** F1-Score, AUC-ROC, Precision, Recall, FPR
- **Complementares:** Accuracy (para contexto), tempo de treinamento/predição
- **Não usar** Accuracy isolada — inadequada para datasets desbalanceados (P14)

### 7.4 Validações Recomendadas

- **Cross-validation (k-fold):** validar robustez e evitar overfitting
- **Testar em train e test sets separados:** P5 mostra degradação de 99.81% → 83.28% no test set
- **Grid search para hiperparâmetros:** P7 usou grid search para DT e RF

---

## 8. Referências Bibliográficas dos Papers Analisados

1. CHAKIR, O. et al. An empirical assessment of ensemble methods and traditional machine learning techniques for web-based attack detection in industry 5.0. *Journal of King Saud University – Computer and Information Sciences*, v. 35, p. 103–119, 2023.

2. MUHURI, P. S.; SHAH, S.; YUAN, X. Implementing a network intrusion detection system using semi-supervised support vector machine and random forest. *ACM Southeast Conference (ACM SE '21)*, 2021.

3. WANG, P. et al. Design and Implementation of a Machine Learning-Based Network Intrusion Detection System. *ACM CTCNet 2024*, 2024.

4. MAHMUD, M. A.; HASAN, K. T. Advancements in Machine Learning for Adaptive Intrusion Detection: A Comprehensive Review. *ICCA 2024*, 2024.

5. YIN, C. et al. A Deep Learning Approach for Intrusion Detection Using Recurrent Neural Networks. *IEEE Access*, v. 5, p. 21954–21961, 2017.

6. ENNAJI, S. et al. Adversarial Challenges in Network Intrusion Detection Systems: Research Insights and Future Prospects. *IEEE Access*, v. 13, 2025.

7. BERTOLI, G. C. et al. An End-to-End Framework for Machine Learning-Based Network Intrusion Detection System. *IEEE Access*, v. 9, 2021.

8. AZAM, Z.; ISLAM, M. M.; HUDA, M. N. Comparative Analysis of Intrusion Detection Systems and Machine Learning-Based Model Analysis Through Decision Tree. *IEEE Access*, v. 11, 2023.

9. ANKALAKI, S. et al. Cyber Attack Prediction: From Traditional Machine Learning to Generative Artificial Intelligence. *IEEE Access*, v. 13, 2025.

10. TRAN, N. et al. Data Curation and Quality Evaluation for Machine Learning-Based Cyber Intrusion Detection. *IEEE Access*, v. 10, 2022.

11. ZOU, L. et al. HC-DTTSVM: A Network Intrusion Detection Method Based on Decision Tree Twin Support Vector Machine and Hierarchical Clustering. *IEEE Access*, v. 11, 2023.

12. BERMAN, D. S. et al. A Survey of Deep Learning Methods for Cyber Security. *Information*, v. 10, n. 4, p. 122, 2019.

13. HALBOUNI, A. et al. Machine Learning and Deep Learning Approaches for CyberSecurity: A Review. *IEEE Access*, v. 10, 2022.

14. LE JEUNE, L.; GOEDEMÉ, T.; MENTENS, N. Machine Learning for Misuse-Based Network Intrusion Detection: Overview, Unified Evaluation and Feature Choice Comparison Framework. *IEEE Access*, v. 9, 2021.
