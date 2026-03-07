# 03 - Aplicação de Técnicas de Transformação

## 1. Objetivo da Etapa

Após a limpeza estrutural dos datasets, tornou-se necessário aplicar transformações adicionais para:

- Preparar os dados para algoritmos de Machine Learning
- Garantir compatibilidade com diferentes tipos de modelos
- Preservar padrões relevantes para previsão de ataques
- Estruturar os dados para uma arquitetura hierárquica (detecção + classificação)

O objetivo final desta etapa foi gerar datasets completamente prontos para modelagem.

---

## 2. Contexto do Problema

O projeto tem como foco a **previsão de ataques cibernéticos**, o que implica:

1. Detectar se o tráfego é benigno ou malicioso.
2. Caso seja malicioso, classificar o tipo de ataque.

Portanto, a preparação dos dados precisava suportar:

- Classificação binária
- Classificação multi-classe
- Diferentes tipos de modelos (árvores, modelos lineares, redes neurais, etc.)

---

## 3. Normalização e Padronização das Features Numéricas

### 3.1 Problema Identificado

Durante a análise estatística, foram observadas:

- Escalas extremamente diferentes entre colunas
- Valores máximos muito elevados (ordem de 10⁹)
- Distribuições altamente assimétricas

Esses fatores podem prejudicar modelos sensíveis à escala, como:

- Regressão Logística
- SVM
- Redes Neurais
- Isolation Forest

---

### 3.2 Estratégia Adotada

Foram geradas versões escaladas dos datasets utilizando:

1. Transformação `log1p` nas colunas com valores muito elevados e não-negativos.
2. Aplicação de `RobustScaler` nas colunas numéricas.

---

### 3.3 Justificativa Técnica

- `log1p` reduz assimetria e comprime valores extremos.
- `RobustScaler` utiliza mediana e IQR, sendo mais resistente a outliers.
- Não foi utilizada padronização simples (StandardScaler) devido à presença de valores extremos.

Importante:

Os outliers não foram removidos, pois em problemas de detecção de intrusão valores extremos podem representar comportamento malicioso legítimo.

---

### 3.4 Arquivos Gerados

- `cic_ids2017_scaled.parquet`
- `unsw_nb15_scaled.parquet`

Esses arquivos são utilizados como base para modelos sensíveis à escala.

---

## 4. Encoding de Variáveis Categóricas

### 4.1 Separação entre Target e Feature

É importante distinguir:

- Target (variável a ser prevista)
- Feature (variáveis de entrada do modelo)

O tratamento aplicado foi diferente para cada tipo.

---

### 4.2 Encoding do Target Multi-classe

Para permitir classificação do tipo de ataque, foi criada a variável:

- `Attack_Type`

Em seguida, foi aplicado **Label Encoding** para gerar:

- `Attack_Type_ID`

Justificativa:

- O encoding é aplicado ao target, não a uma feature.
- Modelos de classificação aceitam rótulos inteiros.
- Evita aumento desnecessário da dimensionalidade.

---

### 4.3 Encoding das Features Categóricas (UNSW-NB15)

No dataset UNSW-NB15 existem colunas categóricas de entrada:

- `proto`
- `state`
- `service`

Foi aplicada técnica de **One-Hot Encoding** nessas colunas.

Justificativa:

- Não cria ordem artificial entre categorias.
- Mantém neutralidade semântica.
- Representa corretamente protocolos e estados de rede.
- É adequado para modelos supervisionados.

---

## 5. Arquitetura Hierárquica de Modelagem

Para suportar a estratégia de previsão em dois níveis, foram gerados dois conjuntos finais para cada dataset:

### 5.1 Dataset para Classificação Binária

Objetivo: Detectar se o tráfego é benigno ou ataque.

Arquivos:

- `cic_ids2017_model_ready_binary.parquet`
- `unsw_nb15_model_ready_binary.parquet`

Contém:

- Todas as features transformadas
- `Binary_Label` como target

---

### 5.2 Dataset para Classificação do Tipo de Ataque

Objetivo: Classificar o tipo de ataque somente quando `Binary_Label = 1`.

Arquivos:

- `cic_ids2017_model_ready_attacktype.parquet`
- `unsw_nb15_model_ready_attacktype.parquet`

Contém:

- Apenas registros maliciosos
- `Attack_Type_ID` como target multi-classe

---

## 6. Engenharia de Features

Nesta etapa, não foram criadas novas features derivadas.

Justificativa:

- Os datasets já contêm engenharia estatística avançada (taxas, médias, variâncias, contagens).
- O foco inicial foi garantir estabilidade estrutural e compatibilidade com modelos.
- Engenharia adicional pode ser realizada em etapa posterior de otimização.

---

## 7. Resultado Final da Etapa

Foram gerados datasets completamente prontos para modelagem:

- Sem valores ausentes
- Sem valores infinitos
- Com escalonamento adequado
- Com encoding aplicado corretamente
- Estruturados para arquitetura de dois estágios

A etapa de transformação conclui a preparação técnica dos dados e habilita o início da fase de modelagem.

---

## 8. Conclusão

A aplicação das técnicas de transformação garantiu:

- Robustez estatística
- Compatibilidade com múltiplos modelos
- Preservação de padrões relevantes para detecção
- Estrutura adequada para um sistema de previsão de ataques

Com isso, o pipeline de pré-processamento encontra-se completo.
Além disso, a separação em dois estágios (detecção binária seguida de classificação do tipo de ataque) permite maior controle operacional em cenários reais, reduzindo alarmes falsos e possibilitando classificação detalhada apenas quando necessário.