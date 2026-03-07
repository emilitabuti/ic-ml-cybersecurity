# 00 - Revisão e Seleção de Fontes

## 1. Contexto e Problema

Projetos de detecção de intrusão frequentemente apresentam limitações como:

- Uso de apenas um dataset
- Dados desatualizados ou pouco realistas
- Falta de diversidade de cenários
- Modelos que não generalizam bem

Além disso, o projeto possui foco em **redes acadêmicas**, exigindo bases que representem tráfego realista com múltiplos tipos de ataques.

Assim, tornou-se necessário selecionar datasets que:

- Fossem públicos e amplamente utilizados
- Representassem cenários realistas
- Permitissem classificação binária e multi-classe
- Possibilitassem comparação entre diferentes contextos

---

## 2. Estratégia de Pesquisa

Foram utilizadas as seguintes palavras-chave:

- "Intrusion Detection Dataset"
- "Network Anomaly Detection Dataset"
- "Academic Network Traffic Dataset"
- "Cyber Attack Dataset"
- "IDS Benchmark Dataset"

A partir da literatura e benchmarks acadêmicos, foram identificados datasets consolidados na área.

---

## 3. Datasets Avaliados

### 3.1 CIC-IDS2017

**Descrição:**  
Dataset desenvolvido pelo Canadian Institute for Cybersecurity simulando ambiente corporativo/acadêmico com tráfego benigno e múltiplos ataques.

**Pontos positivos:**
- Amplamente citado na literatura
- Grande diversidade de ataques
- Estrutura baseada em features estatísticas extraídas de fluxos
- Permite classificação binária e multi-classe

**Limitações identificadas:**
- Inconsistências de encoding no campo de label
- Presença de colunas duplicadas
- Leve desbalanceamento de classes

---

### 3.2 UNSW-NB15

**Descrição:**  
Dataset desenvolvido pela Universidade de New South Wales com tráfego sintético e realista contendo múltiplas categorias de ataque.

**Pontos positivos:**
- Estrutura moderna e organizada
- Campo específico para categoria de ataque (multi-classe)
- Amplamente utilizado em benchmarks acadêmicos

**Limitações identificadas:**
- Forte desbalanceamento entre classes
- Inconsistências nos nomes das categorias
- Presença de registros duplicados

---

## 4. Comparação Estratégica

| Critério                  | CIC-IDS2017 | UNSW-NB15 |
|---------------------------|-------------|------------|
| Volume de dados           | Alto        | Muito alto |
| Classificação binária     | Sim         | Sim        |
| Classificação multi-classe| Sim         | Sim        |
| Desbalanceamento          | Moderado    | Alto       |
| Diversidade de ataques    | Alta        | Média      |

---

## 5. Decisão Final

Foram selecionados:

- CIC-IDS2017 (**primário** — foco deste projeto)
- UNSW-NB15 (secundário — base para validação cruzada futura)

### Justificativa:

1. Complementaridade estrutural entre os datasets
2. Aceitação ampla na comunidade científica
3. Capacidade de suportar experimentos binários e multi-classe
4. Possibilidade de testar generalização entre bases distintas
5. Adequação ao contexto de redes acadêmicas

---

## 6. Autoria

Caroline Guimarães Campos — pipeline de preparação de dados  
Emili Tabuti — integração ao ml-pipeline e camada de modelagem
