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

## Reprodutibilidade

Todas as execuções usam `RANDOM_SEED = 42` definido em `config.py`. Para reproduzir experimentos:

```bash
python -m pytest tests/
```
