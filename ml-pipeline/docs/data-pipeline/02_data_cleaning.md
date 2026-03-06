# 02 - Limpeza e Tratamento dos Dados

## 1. Objetivo da Etapa

Após a consolidação dos datasets, tornou-se necessário garantir:

- Consistência estrutural
- Ausência de duplicações
- Correção de inconsistências
- Tratamento adequado de valores ausentes
- Tratamento apropriado de valores extremos
- Preparação para modelagem

Esta etapa teve como foco transformar os dados brutos em conjuntos confiáveis e prontos para experimentação.

---

## 2. Análise Exploratória Inicial (EDA)

Foi realizada inspeção inicial para:

- Identificação de colunas
- Verificação de tipos de dados
- Distribuição das classes
- Detecção de valores ausentes
- Detecção de valores infinitos
- Análise estatística descritiva (média, desvio, quartis, máximo e mínimo)

### Resultados principais:

#### CIC-IDS2017
- ~1.2 milhões de registros iniciais
- 80 colunas
- Leve desbalanceamento entre benignos e ataques

#### UNSW-NB15
- ~2.28 milhões de registros iniciais
- 50 colunas
- Forte desbalanceamento (≈ 3,8% ataques após limpeza)

---

## 3. Remoção de Duplicatas

### CIC-IDS2017
- 107.987 registros duplicados removidos

### UNSW-NB15
- 695.831 registros duplicados removidos

### Justificativa

Registros duplicados podem:

- Inflar artificialmente padrões
- Viésar o modelo
- Distorcer métricas

A remoção foi realizada mantendo apenas registros únicos.

---

## 4. Correção de Inconsistências

### CIC-IDS2017

- Correção de caracteres corrompidos no campo `Label`
- Padronização de nomes de colunas (remoção de espaços, substituição de símbolos)
- Remoção de colunas duplicadas
- Criação da coluna `Binary_Label`

### UNSW-NB15

- Remoção de espaços extras em `attack_cat`
- Unificação de categorias duplicadas (ex: "Backdoors" → "Backdoor")
- Substituição de valores nulos de categoria por `BENIGN`
- Criação da coluna `Binary_Label`

---

## 5. Tratamento de Valores Ausentes

### CIC-IDS2017

- 94 registros com valores ausentes (~0,0085%)
- Estratégia: remoção das linhas (impacto estatístico irrelevante)

### UNSW-NB15

- Duas colunas com aproximadamente 30% de valores ausentes:
  - `is_ftp_login`
  - `ct_flw_http_mthd`

Análise indicou que os valores ausentes representavam ausência de evento (não aplicável).

Estratégia adotada:
- Substituição por 0

Justificativa:
- Preserva estrutura
- Mantém volume de dados
- Evita perda de 500 mil registros

---

## 6. Tratamento de Valores Infinitos

No CIC-IDS2017 foram encontrados valores infinitos em:

- `Flow_Bytes_s`
- `Flow_Packets_s`

Causa identificada:
- Divisão por zero na duração do fluxo

Estratégia adotada:
1. Substituição de `inf` por `NaN`
2. Preenchimento com 0

Justificativa:
- Mantém integridade do registro
- Evita falhas em algoritmos de Machine Learning
- Preserva comportamento do tráfego

UNSW-NB15 não apresentou valores infinitos.

---

## 7. Estratégia para Outliers

Em problemas de detecção de intrusão, valores extremos podem representar comportamento malicioso legítimo.

Portanto:

- Não foi realizada remoção de outliers
- Optou-se por preservar valores extremos
- Foi criada versão alternativa com transformação robusta

---

## 8. Geração de Versões Transformadas

Para suportar diferentes tipos de modelos, foram geradas versões escaladas dos datasets:

- Aplicação de transformação `log1p` em colunas altamente assimétricas
- Aplicação de `RobustScaler` nas colunas numéricas

Arquivos gerados:

- `cic_ids2017_scaled.parquet`
- `unsw_nb15_scaled.parquet`

Justificativa:

- Permitir uso com modelos sensíveis à escala (SVM, Redes Neurais, Isolation Forest)
- Preservar versão original para modelos baseados em árvore (RandomForest, XGBoost)

---

## 9. Resultado Final da Etapa

Foram gerados quatro datasets finais:

- `cic_ids2017_cleaned.parquet`
- `cic_ids2017_scaled.parquet`
- `unsw_nb15_cleaned.parquet`
- `unsw_nb15_scaled.parquet`

Todos:

- Sem duplicatas
- Sem valores ausentes
- Sem valores infinitos
- Estruturalmente consistentes
- Prontos para etapa de transformação e preparação final para modelagem.

---

## 10. Conclusão

A etapa de limpeza e tratamento garantiu:

- Qualidade estrutural
- Robustez metodológica
- Preparação para experimentação comparativa
- Flexibilidade para diferentes arquiteturas de modelo

Com isso, o pipeline encontra-se pronto para a fase de modelagem e avaliação.