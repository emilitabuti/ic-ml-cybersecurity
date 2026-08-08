# IC ML Cybersecurity

Sistema de previsao de ataques ciberneticos com Machine Learning.

O projeto combina um pipeline temporal de ML, uma API local em FastAPI e um
dashboard React para monitoramento de alertas. A ideia central e analisar
janelas de trafego de rede e emitir previsoes de ataque antes da concretizacao
do evento.

## Visao geral

O repositorio é organizado com dois modulos principais:

- `ml-pipeline/`: processamento de dados, treinamento, avaliacao, artefato de
  modelo e API FastAPI.
- `dashboard/`: interface web em React para visualizar alertas, historico,
  detalhes de previsão e modo de demonstracao.

Tambem existem pastas auxiliares:

- `docs/`: documentos, resumos e materiais de apoio do projeto.
- `demos/`: arquivos relacionados a demonstracoes.

## Tecnologias principais

Backend e ML:

- Python 3.12
- FastAPI
- scikit-learn
- TensorFlow/Keras
- pandas, NumPy e pyarrow
- MLflow para rastreamento de experimentos
- pytest para testes

Frontend:

- React 18
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query
- Recharts
- Vitest e Testing Library

## Estrutura do projeto

```text
ic-ml-cybersecurity/
├── dashboard/          # Frontend React
├── ml-pipeline/        # Pipeline de ML + API FastAPI
├── docs/               # Documentacao e resumos
├── demos/              # Materiais de demonstracao
├── .github/            # Configuracoes do GitHub
├── .gitignore
└── README.md
```

## Como executar

Use dois terminais: um para a API e outro para o dashboard.

### 1. API FastAPI

A partir da raiz do projeto:

```powershell
cd ml-pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Endpoints principais:

- `GET /health`
- `GET /model/info`
- `GET /history`
- `POST /predict`

Documentacao interativa da API:

```text
http://127.0.0.1:8000/docs
```

### 2. Dashboard React

Em outro terminal, a partir da raiz do projeto:

```powershell
cd dashboard
npm install
Copy-Item .env.example .env
npm run dev
```

Acesse:

```text
http://localhost:5173
```

Por padrao, o dashboard procura a API em:

```text
http://127.0.0.1:8000
```

Essa URL pode ser alterada em `dashboard/.env` pela variavel:

```env
VITE_API_URL=http://127.0.0.1:8000
```

## Dados e modelo

Os datasets grandes nao devem ser versionados no Git. Coloque os arquivos brutos
ou processados nas pastas esperadas dentro de `ml-pipeline/data/`, conforme o
README especifico do modulo.

O modelo servido pela API e configurado por:

```env
MODEL_ARTIFACT_PATH=models/model_rf_temporal_v2.pkl
```

No pipeline atual, o protocolo temporal usa UNSW-NB15 com janela de 10 registros
e Random Forest como modelo final.

## Verificacao

### Backend

```powershell
cd ml-pipeline
python -m pytest tests -q
```

### Frontend

```powershell
cd dashboard
npm run build
npm test
```

Se o Vitest tiver timeout ao iniciar workers no Windows, rode:

```powershell
npx vitest run --pool=threads
```

## Observacoes importantes

- A API deve rodar localmente por padrao, em `127.0.0.1`.
- O projeto usa dados publicos ou simulados.
- Para validade, mantenha separacao entre treino, validacao e
  teste.
