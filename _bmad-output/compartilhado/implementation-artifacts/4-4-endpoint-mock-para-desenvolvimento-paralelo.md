# Story 4.4: Endpoint Mock para Desenvolvimento Paralelo

Status: done

## Story

Como desenvolvedora do dashboard (Isabela),
Quero um endpoint mock que retorna predições fixas sem depender do modelo real,
Para que possa desenvolver e testar a interface sem aguardar a conclusão do Epic 3.

## Acceptance Criteria

1. **Dado** que a API FastAPI está rodando
   **Quando** envio `POST /predict/mock`
   **Então** a resposta tem status HTTP 200 e Content-Type `application/json`
   **E** retorna exatamente os campos esperados pelo contrato do `/predict` real: `{ "prediction": "...", "confidence": 0.xx, "model": "...", "timestamp": "ISO8601" }`
   **E** todos os campos usam `snake_case`.

2. **Dado** que envio chamadas sucessivas para `POST /predict/mock`
   **Quando** observo as respostas
   **Então** o mock alterna ciclicamente entre pelo menos 3 cenários: ataque crítico, tráfego suspeito e tráfego normal
   **E** os valores de `confidence` são numéricos entre `0.0` e `1.0`.

3. **Dado** que acesso `GET /docs` ou o schema OpenAPI em `/openapi.json`
   **Quando** procuro pelo endpoint mock
   **Então** `POST /predict/mock` está documentado automaticamente pelo FastAPI com schema de resposta compatível com o contrato do `/predict` real.

4. **Dado** que Epic 2 e Epic 3 ainda estão em backlog
   **Quando** executo a API e os testes do mock
   **Então** nenhuma dependência de feature engineering, treino, artefato serializado ou carregamento de modelo real é necessária.

## Tasks / Subtasks

- [x] Task 1: Escrever testes de contrato para `POST /predict/mock` antes da implementação (AC: #1, #3, #4)
  - [x] Subtask 1.1: Criar teste com `fastapi.testclient.TestClient` validando status 200, JSON e campos `prediction`, `confidence`, `model`, `timestamp`
  - [x] Subtask 1.2: Validar que `timestamp` é ISO 8601 parseável e que `confidence` fica entre `0.0` e `1.0`
  - [x] Subtask 1.3: Validar que `/openapi.json` contém `POST /predict/mock`

- [x] Task 2: Escrever teste de ciclo de respostas antes da implementação (AC: #2)
  - [x] Subtask 2.1: Chamar `POST /predict/mock` pelo menos 4 vezes e validar que os 3 cenários aparecem
  - [x] Subtask 2.2: Validar que a quarta resposta reinicia o ciclo no primeiro cenário

- [x] Task 3: Implementar schemas Pydantic do contrato de predição (AC: #1, #3)
  - [x] Subtask 3.1: Criar `src/api/schemas/prediction.py` com `PredictionResponse`
  - [x] Subtask 3.2: Garantir tipos: `prediction: str`, `confidence: float`, `model: str`, `timestamp: str`

- [x] Task 4: Implementar rota mock sem dependência de modelo real (AC: #1, #2, #4)
  - [x] Subtask 4.1: Criar `src/api/routes/predict.py` com `APIRouter` e `POST /predict/mock`
  - [x] Subtask 4.2: Usar uma sequência cíclica determinística com 3 respostas: ataque crítico, suspeito e tráfego normal
  - [x] Subtask 4.3: Gerar `timestamp` em UTC no formato ISO 8601
  - [x] Subtask 4.4: Não importar módulos de `src.features`, `src.training` ou `src.models`

- [x] Task 5: Registrar rota no app FastAPI e validar regressão completa (AC: #1–#4)
  - [x] Subtask 5.1: Incluir o router em `src/api/main.py`
  - [x] Subtask 5.2: Rodar testes novos primeiro em vermelho, depois em verde
  - [x] Subtask 5.3: Rodar a suíte completa de `ml-pipeline` sem regressão

## Dev Notes

### Ordem fora da sequência

Esta story deve ser implementada antes das Stories 4.1, 4.2 e 4.3 por decisão já documentada em `epics.md`:

> Story 4.4 (Endpoint Mock) deve ser implementada antes das Stories 4.1–4.3 para habilitar o desenvolvimento paralelo do Dashboard (Epic 5) sem aguardar o modelo real.

Escopo autorizado: apenas `POST /predict/mock` com dados simulados. Não implementar o modelo real, `POST /predict`, `GET /model/info` nem `GET /history` nesta story.

### Contexto técnico atual

```
ml-pipeline/
├── src/api/main.py              # FastAPI app + CORS + GET /health
├── src/api/routes/__init__.py   # existe, vazio
├── src/api/schemas/__init__.py  # existe, vazio
├── src/api/services/__init__.py # existe, vazio
└── tests/test_scaffolding.py    # já testa import do app e GET /health
```

### Contrato de resposta

O mock deve reutilizar o mesmo formato planejado para `/predict` em `architecture.md`:

```json
{
  "prediction": "DDoS",
  "confidence": 0.94,
  "model": "random_forest",
  "timestamp": "2026-02-21T14:00:00Z"
}
```

Para esta story, `model` deve deixar claro que é simulado, por exemplo `mock-cyclic-v1`. O campo `timestamp` deve ser gerado no momento da requisição em UTC e ser parseável via `datetime.fromisoformat(...)` após substituir `Z` por `+00:00`.

### Respostas simuladas obrigatórias

Usar pelo menos estes três cenários, em ordem determinística:

1. Ataque crítico: `prediction="DDoS"`, `confidence >= 0.90`
2. Suspeito: `prediction="Suspicious Traffic"`, `0.70 <= confidence < 0.90`
3. Normal: `prediction="Normal Traffic"`, `confidence < 0.70`

A quarta chamada deve voltar ao primeiro cenário. O ciclo precisa ser estável o suficiente para testes automatizados.

### Arquitetura e padrões obrigatórios

- FastAPI em `ml-pipeline/src/api/`
- Rotas em `src/api/routes/`
- Schemas Pydantic em `src/api/schemas/`
- Campos JSON em `snake_case`
- Resposta direta, sem envelope
- Timestamps ISO 8601 em toda API
- `logging` em vez de `print()` se log for necessário
- Sem dependências novas
- Sem import de feature engineering, treinamento, serialização ou artefatos de modelo

### Testing Requirements

- Testes Python em `ml-pipeline/tests/`
- Usar `fastapi.testclient.TestClient`, como em `tests/test_scaffolding.py`
- Rodar primeiro o teste novo para confirmar falha antes do código
- Rodar a suíte completa com:

```bash
cd ml-pipeline
python -m pytest tests/ -q
```

### References

- [Source: epics.md#Epic-4] — ordem especial da Story 4.4 antes de 4.1–4.3, FR26 e ACs do endpoint mock
- [Source: architecture.md#API-&-Communication-Patterns] — formato REST, resposta direta, campos JSON e timestamp ISO 8601
- [Source: architecture.md#Project-Structure-&-Boundaries] — localização esperada de `src/api/routes/` e `src/api/schemas/`
- [Source: ml-pipeline/src/api/main.py] — estado atual do FastAPI (`GET /health`, CORS, título e versão)
- [Source: ml-pipeline/tests/test_scaffolding.py] — padrão existente de testes com `TestClient`
- [Source: sprint-status.yaml] — `4-4-endpoint-mock-para-desenvolvimento-paralelo` deve sair de `backlog` para `ready-for-dev` antes do dev-story

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- RED: `.venv/bin/python -m pytest tests/test_api_predict_mock.py -q` falhou com `ModuleNotFoundError: No module named 'src.api.routes.predict'`
- GREEN: `.venv/bin/python -m pytest tests/test_api_predict_mock.py -q` → 3 passed
- REGRESSION: `.venv/bin/python -m pytest tests/ -q` → 113 passed, 1 warning (`StarletteDeprecationWarning` do `fastapi.testclient`)
- CODE REVIEW FIX: `.venv/bin/python -m pytest tests/test_api_predict_mock.py -q` → 4 passed
- FINAL REGRESSION: `.venv/bin/python -m pytest tests/ -q` → 114 passed, 1 warning (`StarletteDeprecationWarning` do `fastapi.testclient`)

### Completion Notes List

- Implementado `POST /predict/mock` em FastAPI com resposta direta no contrato planejado do `/predict` real.
- Criado ciclo determinístico de 3 cenários: `DDoS`, `Suspicious Traffic`, `Normal Traffic`; quarta chamada reinicia no primeiro cenário.
- Criado `PredictionResponse` com Pydantic para schema OpenAPI automático.
- Endpoint não importa nem depende de `src.features`, `src.training`, `src.models`, artefatos serializados ou Epic 2/3.
- Restaurados diretórios obrigatórios do scaffolding com `.gitkeep` e exceções específicas no `.gitignore`, mantendo datasets/modelos reais ignorados.
- **[Code Review Fix]** Adicionado teste explícito garantindo que a rota mock não importa módulos ainda não implementados do pipeline de ML.

### File List

.gitignore
_bmad-output/compartilhado/implementation-artifacts/4-4-endpoint-mock-para-desenvolvimento-paralelo.md
_bmad-output/compartilhado/implementation-artifacts/sprint-status.yaml
ml-pipeline/data/raw/.gitkeep
ml-pipeline/data/processed/.gitkeep
ml-pipeline/data/schema/.gitkeep
ml-pipeline/models/.gitkeep
ml-pipeline/notebooks/.gitkeep
ml-pipeline/src/api/main.py
ml-pipeline/src/api/routes/predict.py
ml-pipeline/src/api/schemas/prediction.py
ml-pipeline/tests/test_api_predict_mock.py

## Change Log

| Data | Mudança |
|---|---|
| 2026-07-25 | Story criada fora da ordem sequencial por decisão registrada em `epics.md`; endpoint mock implementado em TDD e pronto para code review |
| 2026-07-25 | Code review executado; cobertura do boundary Epic 2/3 adicionada; story marcada como done |

## Senior Developer Review (AI)

### Review Date

2026-07-25

### Outcome

Approve — todos os ACs da Story 4.4 foram implementados e validados.

### Findings

- **Medium — Test gap:** AC #4 exigia independência de Epic 2/3, mas a primeira versão dos testes validava apenas comportamento externo. Correção aplicada em `tests/test_api_predict_mock.py`: teste `test_predict_mock_route_does_not_depend_on_unimplemented_ml_pipeline`.

### Action Items

- [x] [AI-Review][Medium] Adicionar teste explícito contra import acidental de `src.features`, `src.training` ou `src.models` na rota mock.

### Verification

- `.venv/bin/python -m pytest tests/test_api_predict_mock.py -q` → 4 passed
- `.venv/bin/python -m pytest tests/ -q` → 114 passed, 1 warning (`StarletteDeprecationWarning` do `fastapi.testclient`)
