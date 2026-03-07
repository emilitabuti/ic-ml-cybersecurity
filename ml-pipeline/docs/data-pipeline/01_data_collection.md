# 01 - Desenvolvimento dos Scripts de Coleta

## 1. Problema Identificado

Datasets públicos geralmente são disponibilizados:

- Em múltiplos arquivos
- Sem padronização estrutural
- Sem organização pronta para pipelines de Machine Learning

Isso dificulta:

- Reprodutibilidade
- Consolidação
- Automação do processo

Era necessário criar scripts que:

- Consolidassem os arquivos
- Organizassem os dados
- Garantissem reprodutibilidade

---

## 2. Organização do Projeto

Foi criada a seguinte estrutura:
```
data/
├── raw/
├── processed/
├── scripts/
└── docs/
```

Objetivo de cada diretório:

- `raw/` → armazenamento dos dados brutos originais
- `processed/` → datasets consolidados e limpos
- `scripts/` → automação do pipeline
- `docs/` → documentação técnica do projeto

---

## 3. Coleta – CIC-IDS2017

### 3.1 Ação Realizada

- Download dos arquivos no formato `.parquet`
- Consolidação dos arquivos em um único dataset
- Armazenamento centralizado na pasta `processed`

### 3.2 Resultado

- Aproximadamente 1.2 milhões de registros brutos
- 80 colunas
- Dataset consolidado e pronto para a etapa de limpeza

---

## 4. Coleta – UNSW-NB15

### 4.1 Desenvolvimento do Script

Foi criado o script:
''' scripts/collect_unsw_nb15.py '''


Funções implementadas:

- Leitura automática dos arquivos `.parquet`
- Consolidação em um único DataFrame
- Salvamento no formato `.parquet`
- Impressão de informações básicas (linhas e colunas)

### 4.2 Execução

O script foi testado e executado com sucesso, garantindo que todos os arquivos fossem carregados corretamente.

### 4.3 Resultado Obtido

- 2.280.090 registros
- 50 colunas
- Arquivo consolidado salvo em:
``` data/processed/unsw_nb15_raw_merged.parquet ```

---

## 5. Justificativa Técnica

A criação de scripts de coleta garante:

- Reprodutibilidade do experimento
- Padronização do fluxo de dados
- Redução de erros manuais
- Estruturação adequada para a etapa de limpeza

Além disso, automatizar a coleta permite que qualquer pessoa reproduza o experimento apenas executando os scripts.

---

## 6. Entregável da Etapa

✔ Scripts funcionais de coleta  
✔ Consolidação automatizada dos datasets  
✔ Dados centralizados em formato padronizado  
✔ Estrutura organizada para tratamento posterior  

Esta etapa estabelece a base técnica necessária para as fases seguintes de:

- Limpeza e tratamento
- Engenharia de atributos
- Modelagem
- Avaliação de desempenho