# IC ML Cybersecurity — ML Pipeline

Componente Python do projeto de Iniciação Científica: treino, avaliação e serving de modelos de ML para detecção de intrusões de rede (CICIDS2017).

## Pré-requisitos

- Python 3.10+
- `pip` atualizado

## Instalação

```bash
# Na raiz do ml-pipeline/
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

pip install -r requirements.txt
cp .env.example .env
```

## Estrutura

```
ml-pipeline/
├── config.py           # Configurações globais (RANDOM_SEED, WINDOW_SIZE, ...)
├── requirements.txt    # Dependências com versões fixadas
├── data/
│   ├── raw/            # Dataset CICIDS2017 original (não versionado)
│   ├── processed/      # CSV pré-processado por Caroline
│   └── schema/         # features_schema.json — contrato de dados
├── models/             # Modelos serializados (.pkl, .h5)
├── notebooks/          # Exploração e prototipagem
├── src/
│   ├── data/           # Carregamento e validação do dataset
│   ├── features/       # Feature engineering e sliding window
│   ├── training/       # Scripts de treino por modelo
│   ├── models/         # Serialização do modelo vencedor
│   └── api/            # FastAPI (serving de predições)
└── tests/              # Testes unitários e de integração
```

## Executar a API

```bash
source .venv/bin/activate
uvicorn src.api.main:app --reload
# Acesse: http://127.0.0.1:8000/health
# Docs:   http://127.0.0.1:8000/docs
```

## Reprodutibilidade Científica

**Objetivo:** pesquisador externo consegue reproduzir os experimentos em ≤ 30 minutos de setup.

Todas as execuções usam `RANDOM_SEED = 42` definido em `config.py`, garantindo resultados idênticos entre runs. A variação máxima aceita entre runs com mesmo seed, mesmo dataset e mesmos hiperparâmetros é **≤ 0,01%** em todas as métricas.

### Pré-requisitos (≈ 2 min de verificação)

- Python 3.10+
- `pip` atualizado (`pip install --upgrade pip`)
- `git`
- ~500 MB de espaço em disco (ambiente + dependências, sem dataset)
- ~3 GB adicionais para o dataset CICIDS2017

### 1. Clonar e instalar (≈ 5 min)

```bash
git clone https://github.com/emili-tabuti/ic-ml-cybersecurity.git
cd ic-ml-cybersecurity/ml-pipeline

python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

pip install -r requirements.txt
cp .env.example .env
```

### 2. Verificar integridade do ambiente (≈ 2 min)

```bash
# Dentro de ml-pipeline/ com o venv ativo
python -m pytest tests/ -v
# Esperado: todos os testes passando — sem falhas
```

### 3. Preparar o dataset (≈ variável)

O dataset CICIDS2017 **não está versionado no repositório** (~2,8 GB). Para obter:

1. Acesse: [Canadian Institute for Cybersecurity — IDS 2017](https://www.unb.ca/cic/datasets/ids-2017.html)
2. Faça o download dos arquivos CSV
3. Coloque os arquivos em `ml-pipeline/data/raw/`

```
ml-pipeline/data/raw/
├── Monday-WorkingHours.pcap_ISCX.csv
├── Tuesday-WorkingHours.pcap_ISCX.csv
├── Wednesday-workingHours.pcap_ISCX.csv
├── Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv
├── Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv
├── Friday-WorkingHours-Morning.pcap_ISCX.csv
├── Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv
└── Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv
```

### 4. Executar o pipeline de dados (≈ 10 min)

O pipeline de dados está implementado em `src/data/pipeline/`. Após preparar o dataset:

```python
# Exemplo de uso — execute via Python REPL ou notebook
from src.data.data_loader import load_binary_dataset
from src.data.data_splitter import split_train_test
import config

# Carregar e validar o dataset
X, y = load_binary_dataset(dataset="cic")
print(f"Dataset: {X.shape[0]} amostras, {X.shape[1]} features")
print(f"Classes: {y.value_counts().to_dict()}")

# Dividir em treino/teste (estratificado, sem data leakage)
X_train, X_test, y_train, y_test = split_train_test(X, y)
print(f"Treino: {X_train.shape[0]} | Teste: {X_test.shape[0]}")
```

O split é reprodutível: usa `RANDOM_SEED = 42` e é estratificado por label (proporção de classes preservada).

### 5. Executar o pipeline de treino

> ⚠️ **Nota:** Os scripts de treino serão implementados no Epic 3. Os comandos abaixo mostram a estrutura esperada e serão funcionais após as Stories 3.2–3.4.

```bash
# [a implementar — Story 3.2] Random Forest com k-fold
python src/training/train_rf.py

# [a implementar — Story 3.3] Decision Tree com k-fold
python src/training/train_dt.py

# [a implementar — Story 3.4] LSTM/MLP com k-fold
python src/training/train_lstm.py
```

Quando implementados, cada script registra automaticamente no MLflow: hiperparâmetros, métricas (F1, AUC-ROC, FPR por classe), artefatos do modelo e seed usado.

### 6. Acessar métricas no MLflow UI (≈ 1 min)

```bash
# Dentro de ml-pipeline/ com o venv ativo
mlflow ui
# Acesse: http://127.0.0.1:5000

# Ou especificando o diretório de experimentos
mlflow ui --backend-store-uri ./mlruns
```

O MLflow UI exibe: comparação de runs, métricas por experimento, hiperparâmetros usados e artefatos gerados.

### O que NÃO está versionado

```gitignore
data/raw/       # Dataset CICIDS2017 (~2,8 GB) — obter via link acima
data/processed/ # Dados intermediários gerados localmente
models/         # Modelos serializados (.pkl, .joblib, .h5)
mlruns/         # Experimentos MLflow — gerados localmente ao treinar
.env            # Variáveis de ambiente locais
.venv/          # Ambiente virtual Python
__pycache__/
```

