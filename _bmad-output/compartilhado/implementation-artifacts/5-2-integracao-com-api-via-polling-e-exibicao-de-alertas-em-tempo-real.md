# Story 5.2: Integração com API via Polling e Exibição de Alertas em Tempo Real

Status: done

## Story

Como analista de segurança (Ana),
Quero receber alertas de ameaças previstas automaticamente no dashboard sem refresh manual,
Para que possa monitorar a rede de forma passiva e ser notificada antes da concretização de um ataque.

## Acceptance Criteria

**Dado** que a API FastAPI está rodando em `http://127.0.0.1:8000`
**Quando** abro o dashboard na seção Monitor
**Então** o TanStack Query faz polling a cada 5 segundos (configurável via `POLLING_INTERVAL_MS` em `src/config.ts`) em `GET /history`
**E** novos alertas aparecem automaticamente na lista sem refresh da página
**E** cada AlertCard exibe: tipo de ameaça, nível de confiança (%), timestamp da janela e badge de severidade por cor (critical `#EF4444` / warning `#F59E0B` / safe `#10B981`)
**E** a severidade é comunicada com cor + ícone + label textual — nunca apenas cor isolada (acessibilidade WCAG AA)
**E** o badge de contagem de alertas ativos no título da aba do browser atualiza em tempo real

## Tasks / Subtasks

- [x] Task 1: Formalizar contrato TypeScript e acesso único à API (AC: polling em `GET /history`)
  - [x] Subtask 1.1: Criar `dashboard/src/types/api.ts` com o tipo espelhado do Pydantic `PredictionResponse` (`prediction`, `confidence`, `model`, `timestamp`)
  - [x] Subtask 1.2: Expandir `dashboard/src/services/api.ts` com `getPredictionHistory()` usando exclusivamente `GET /history`
  - [x] Subtask 1.3: Manter `API_BASE_URL` e `POLLING_INTERVAL_MS` centralizados em `dashboard/src/config.ts`
- [x] Task 2: Implementar polling com TanStack Query (AC: 5s configurável, atualização sem refresh)
  - [x] Subtask 2.1: Criar `dashboard/src/hooks/usePredictions.ts` com `useQuery`, `refetchInterval: POLLING_INTERVAL_MS` e `queryKey` estável
  - [x] Subtask 2.2: Criar estados reutilizáveis `LoadingSpinner` e `ErrorAlert` para loading/error de server state
- [x] Task 3: Exibir AlertCards acessíveis na seção Monitor (AC: tipo, confiança, timestamp, severidade cor + ícone + texto)
  - [x] Subtask 3.1: Criar `dashboard/src/components/alerts/AlertCard.tsx`
  - [x] Subtask 3.2: Atualizar `MonitorSection` para renderizar alertas vindos do hook, preservando a legenda da Story 5.1
  - [x] Subtask 3.3: Atualizar ou substituir a tabela placeholder sem quebrar os componentes de 5.1
- [x] Task 4: Atualizar métricas e título da aba do browser (AC: badge de contagem em tempo real)
  - [x] Subtask 4.1: Permitir que `Header` receba métricas calculadas da lista de alertas
  - [x] Subtask 4.2: Atualizar `document.title` com a contagem de alertas ativos e limpar/restaurar no unmount
- [x] Task 5: Cobrir com testes em TDD e validar
  - [x] Subtask 5.1: Adicionar Vitest/Testing Library se o dashboard ainda não tiver runner de testes configurado
  - [x] Subtask 5.2: Testar `getPredictionHistory()` chamando `GET /history`
  - [x] Subtask 5.3: Testar `usePredictions` ou a seção Monitor com polling configurado
  - [x] Subtask 5.4: Testar `AlertCard` com severidade comunicada por texto + ícone/label, não só cor
  - [x] Subtask 5.5: Rodar `npm run build` e `npm run lint` no final

## Dev Notes

### Fonte de verdade

- `epics.md`, Epic 5, Story 5.2 define polling em `GET /history`, AlertCards com tipo de ameaça, confiança, timestamp e badge de severidade, além do badge de contagem no título da aba.
- `architecture.md` define React + TypeScript + Tailwind + shadcn/ui, TanStack Query v5 para server state, polling REST a cada 5s, `src/services/api.ts` como ponto único de acesso à FastAPI, `src/types/api.ts` para tipos espelhados dos schemas Pydantic e timestamps ISO 8601.
- Story 5.1 já entregou o AppShell, `SeverityBadge`, `severityFromConfidence`, legenda de severidade e tabela placeholder. Não regredir sidebar fixa, header com 4 cards, tema escuro, fontes e navegação por estado local sem router.

### Guardrails técnicos

- Não fazer `fetch` direto em componentes; usar `dashboard/src/services/api.ts`.
- Não criar router nem páginas novas; o dashboard continua single-page com estado local em `App.tsx`.
- Não introduzir banco de dados, WebSocket, Kafka ou persistência nova; a arquitetura oficial usa polling REST e histórico em memória no backend.
- O frontend deve aceitar o formato direto de `/history`: lista de objetos compatíveis com `PredictionResponse`.
- Dados de demo devem permanecer sintéticos/públicos, sem dados pessoais ou sensíveis (NFR12).
- A severidade deve reutilizar `dashboard/src/lib/severity.ts` e `SeverityBadge`, mantendo cor + ícone + label textual para WCAG AA.

### Observação sobre backend/API real

Story 4.3 implementou `GET /history` real, alimentado pelas respostas de `POST /predict`. O dashboard consome esse endpoint diretamente. Para demo do cenário SYN flood sem mock, use `python -m src.evaluation.scenarios.send_real_predictions_to_api` a partir de `ml-pipeline/`; o script chama `POST /predict` e popula o histórico em memória.

### Project Structure Notes

- Arquivos esperados no dashboard:
  - `dashboard/src/types/api.ts`
  - `dashboard/src/hooks/usePredictions.ts`
  - `dashboard/src/components/alerts/AlertCard.tsx`
  - `dashboard/src/components/ui/LoadingSpinner.tsx`
  - `dashboard/src/components/ui/ErrorAlert.tsx`
  - testes co-localizados ou em `dashboard/src/**/__tests__`

### References

- `_bmad-output/compartilhado/planning-artifacts/epics.md` — Epic 5, Stories 5.1 e 5.2
- `_bmad-output/compartilhado/planning-artifacts/architecture.md` — API & Communication Patterns, Frontend Architecture, Process Patterns, Project Structure
- `_bmad-output/compartilhado/implementation-artifacts/5-1-scaffolding-do-dashboard-e-layout-command-center.md`
- `ml-pipeline/src/api/schemas/prediction.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- RED: `npm run test` falhou por `apiClient.getPredictionHistory`, `usePredictions` e `AlertCard` inexistentes.
- GREEN: `npm run test` passou com 4 arquivos / 4 testes.
- Validação frontend: `npm run build` passou.
- Validação frontend: `npm run lint` passou com 1 warning pré-existente em `dashboard/src/components/ui/button.tsx`.
- Validação backend mock: `py -m py_compile src\api\routes\predict.py tests\test_api_predict_mock.py` passou.
- `py -m pytest tests\test_api_predict_mock.py` não executou porque o ambiente Python ativo não tem `fastapi` instalado.
- CR: polling duplicado removido ao levantar o estado de `usePredictions` para `App` e passar dados por props para `MonitorSection`.

### Completion Notes List

- Implementado contrato TypeScript de `PredictionResponse` e cliente `GET /history` via `apiClient.getPredictionHistory()`.
- Implementado `usePredictions` com TanStack Query e `refetchInterval` configurado por `POLLING_INTERVAL_MS`.
- Implementado `AlertCard` com tipo de ameaça, confiança em %, timestamp, modelo e severidade por cor + ícone + label textual.
- `MonitorSection` agora renderiza loading, erro, vazio e lista de AlertCards sem remover a legenda de severidade da Story 5.1.
- `Header` recebe métricas em tempo real para alertas ativos e janelas analisadas; `App` atualiza `document.title` com a contagem de alertas ativos.
- Integração ajustada para o `GET /history` real da Story 4.3; o cenário SYN flood alimenta o histórico via `POST /predict`.
- Code review executado e ajuste aplicado: `MonitorSection` não abre mais um segundo observer da mesma query.

### File List

- `_bmad-output/compartilhado/implementation-artifacts/5-2-integracao-com-api-via-polling-e-exibicao-de-alertas-em-tempo-real.md`
- `_bmad-output/compartilhado/implementation-artifacts/sprint-status.yaml`
- `dashboard/package.json`
- `dashboard/package-lock.json`
- `dashboard/vite.config.ts`
- `dashboard/src/App.tsx`
- `dashboard/src/App.test.tsx`
- `dashboard/src/components/alerts/AlertCard.tsx`
- `dashboard/src/components/alerts/AlertCard.test.tsx`
- `dashboard/src/components/layout/Header.tsx`
- `dashboard/src/components/sections/MonitorSection.tsx`
- `dashboard/src/components/ui/ErrorAlert.tsx`
- `dashboard/src/components/ui/LoadingSpinner.tsx`
- `dashboard/src/hooks/usePredictions.ts`
- `dashboard/src/hooks/usePredictions.test.tsx`
- `dashboard/src/lib/severity.ts`
- `dashboard/src/services/api.ts`
- `dashboard/src/services/api.test.ts`
- `dashboard/src/test/setup.ts`
- `dashboard/src/types/api.ts`
- `ml-pipeline/src/evaluation/scenarios/send_real_predictions_to_api.py`

## Change Log

| Data | Mudança |
|---|---|
| 2026-07-26 | Story criada via BMAD CS com contexto de `epics.md`, `architecture.md` e Story 5.1 |
| 2026-07-26 | Story implementada via BMAD DS com polling TanStack Query, AlertCards, métricas no header, título da aba e histórico mock |
| 2026-07-26 | CR aplicado: removido polling duplicado e Story marcada como done |
| 2026-07-29 | Integração com Epic 4 real: removida dependência de histórico mock e adicionado alimentador via `POST /predict` |

## Senior Developer Review (AI)

### Review Outcome

Approve — ajustes aplicados durante o CR.

### Findings

- [x] [Medium] `App` e `MonitorSection` chamavam `usePredictions()` separadamente, criando observers duplicados para o mesmo polling. Corrigido levantando o hook para `App` e passando `predictions/isLoading/error` por props para `MonitorSection`.

### Validation

- `npm run test` — passou, 4 arquivos / 4 testes.
- `npm run build` — passou.
- `npm run lint` — passou com 1 warning pré-existente em `dashboard/src/components/ui/button.tsx`.
- `py -m py_compile src\api\routes\predict.py tests\test_api_predict_mock.py` — passou.
