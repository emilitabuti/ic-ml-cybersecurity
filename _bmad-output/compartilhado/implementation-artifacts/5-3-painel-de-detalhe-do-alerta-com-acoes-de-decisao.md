# Story 5.3: Painel de Detalhe do Alerta com Ações de Decisão

Status: done

## Story

Como analista de segurança (Ana),
Quero clicar em um alerta e ver seus detalhes completos com opções de decisão inline,
Para que possa avaliar a ameaça e agir em ≤ 2 cliques sem sair do dashboard.

## Acceptance Criteria

**Dado** que há alertas na lista da seção Monitor
**Quando** clico em um AlertCard
**Então** um painel de detalhe abre inline (sem navegação para outra página) exibindo: tipo de ataque previsto, nível de confiança (%), janela temporal (timestamp início–fim) e identificador do modelo que gerou a predição
**E** o painel exibe as top 3 features de tráfego que motivaram a predição (nome em monospace + valor observado + delta vs. baseline)
**E** três botões de ação estão visíveis e funcionais: Confirmar (alerta é ameaça real) / Falso Positivo / Ver Histórico
**E** após a decisão, um toast aparece por 5 segundos com opção de desfazer a ação
**E** o alerta tratado muda de cor/estado imediatamente sem recarregar a página

## Tasks / Subtasks

- [x] Task 1: Modelar estado local de seleção e decisão do alerta (AC: clique abre detalhe, estado muda sem reload)
  - [x] Subtask 1.1: Criar helpers em `dashboard/src/lib/alerts.ts` para `getAlertId()`, janela temporal mock e top features mock derivadas de `PredictionResponse`
  - [x] Subtask 1.2: Em `App.tsx`, manter estado local de decisões por alerta (`pending`, `confirmed`, `false_positive`) sem persistência/backend
  - [x] Subtask 1.3: Passar callbacks e estado para `MonitorSection` sem criar polling duplicado
- [x] Task 2: Tornar AlertCard selecionável e mostrar estado de tratamento (AC: clique, cor/estado imediato)
  - [x] Subtask 2.1: Atualizar `AlertCard` para aceitar `onSelect`, `isSelected` e `decisionStatus`
  - [x] Subtask 2.2: Exibir status textual do alerta tratado além da severidade
  - [x] Subtask 2.3: Garantir affordance acessível (`button`/`aria-pressed`) para clique no card
- [x] Task 3: Implementar painel inline de detalhe (AC: detalhe completo e top 3 features)
  - [x] Subtask 3.1: Criar `dashboard/src/components/alerts/AlertDetailPanel.tsx`
  - [x] Subtask 3.2: Exibir tipo de ataque, confiança, janela temporal início–fim, modelo e top 3 features em monospace
  - [x] Subtask 3.3: Manter painel na seção Monitor, sem router e sem navegação para outra página
- [x] Task 4: Implementar ações de decisão e toast com desfazer (AC: 3 botões, toast 5s, desfazer)
  - [x] Subtask 4.1: Confirmar define status `confirmed` localmente
  - [x] Subtask 4.2: Falso Positivo define status `false_positive` localmente
  - [x] Subtask 4.3: Ver Histórico troca para seção Histórico existente, sem implementar filtros/lista da Story 5.4
  - [x] Subtask 4.4: Criar toast local com timeout de 5s e botão Desfazer que restaura o status anterior
- [x] Task 5: Cobrir com testes em TDD e validar
  - [x] Subtask 5.1: Testar clique no AlertCard abrindo painel inline
  - [x] Subtask 5.2: Testar top 3 features e janela temporal no painel
  - [x] Subtask 5.3: Testar Confirmar/Falso Positivo, mudança imediata de estado e toast com desfazer
  - [x] Subtask 5.4: Testar Ver Histórico trocando a seção sem implementar a Story 5.4
  - [x] Subtask 5.5: Rodar `npm run test`, `npm run build` e `npm run lint`

## Dev Notes

### Fonte de verdade

- `epics.md`, Epic 5, Story 5.3 define painel de detalhe inline, top 3 features, ações Confirmar/Falso Positivo/Ver Histórico, toast 5s com desfazer e mudança visual imediata.
- `architecture.md` mantém frontend single-page sem router, `src/services/api.ts` como acesso único à API, sem banco de dados formal e sem persistência entre reinicializações.
- Story 5.2 já implementou `GET /history`, `usePredictions`, `AlertCard`, métricas no header e title badge. Não criar segundo polling nem regredir a 5.2.

### Guardrails técnicos

- Decisões de alerta nesta story são estado local de UI; não gravar em backend e não implementar histórico filtrável/feedback persistente da Story 5.4.
- `Ver Histórico` deve apenas mudar para a seção Histório/placeholder existente, mantendo o escopo de 5.4 intacto.
- Como a API mock atual não fornece top features nem janela início–fim, usar helpers determinísticos de mock no frontend, derivados de `PredictionResponse`, e manter isso explicitamente isolado em `dashboard/src/lib/alerts.ts`.
- Não implementar SlidingWindowChart (Story 5.7).
- Manter acessibilidade: cards clicáveis devem ser botões ou ter semântica equivalente; ações precisam de texto visível.

### Previous Story Intelligence

- 5.2 corrigiu polling duplicado durante CR: `usePredictions` deve permanecer centralizado em `App.tsx`, e componentes recebem dados por props.
- 5.2 adicionou Vitest/Testing Library; novos testes devem usar o runner existente.
- `npm run lint` passa com 1 warning pré-existente em `dashboard/src/components/ui/button.tsx`.

### Project Structure Notes

- Arquivos esperados:
  - `dashboard/src/lib/alerts.ts`
  - `dashboard/src/components/alerts/AlertDetailPanel.tsx`
  - `dashboard/src/components/alerts/DecisionToast.tsx` ou equivalente local
  - Atualizações em `AlertCard`, `MonitorSection` e `App`

### References

- `_bmad-output/compartilhado/planning-artifacts/epics.md` — Epic 5, Story 5.3
- `_bmad-output/compartilhado/planning-artifacts/architecture.md` — Frontend Architecture, Storage & Persistence, API Boundary
- `_bmad-output/compartilhado/implementation-artifacts/5-2-integracao-com-api-via-polling-e-exibicao-de-alertas-em-tempo-real.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- RED: `npm run test -- App.test.tsx` falhou esperando card selecionável, painel inline, ações e toast ainda inexistentes.
- GREEN: `npm run test` passou com 4 arquivos / 5 testes.
- Validação frontend: `npm run build` passou.
- Validação frontend: `npm run lint` passou com 1 warning pré-existente em `dashboard/src/components/ui/button.tsx`.
- CR: verificado que o polling continua centralizado em `App`, sem `fetch` direto em componentes, sem persistência local/backend e sem escopo de 5.4/5.7.

### Completion Notes List

- Implementado estado local de seleção e decisão de alerta em `App.tsx`, sem backend/persistência.
- Implementados helpers determinísticos em `dashboard/src/lib/alerts.ts` para ID, janela temporal mock e top 3 features mock.
- `AlertCard` agora é selecionável via `role="button"`, `aria-pressed`, clique e teclado, exibindo status textual (`Pendente`, `Confirmado`, `Falso positivo`).
- Implementado `AlertDetailPanel` inline com tipo, confiança, janela temporal, modelo, top 3 features e ações Confirmar/Falso Positivo/Ver Histórico.
- Implementado toast local com opção Desfazer por 5 segundos.
- `Ver Histórico` troca para a seção Histórico existente sem implementar filtros/lista da Story 5.4.

### File List

- `_bmad-output/compartilhado/implementation-artifacts/5-3-painel-de-detalhe-do-alerta-com-acoes-de-decisao.md`
- `_bmad-output/compartilhado/implementation-artifacts/sprint-status.yaml`
- `dashboard/src/App.tsx`
- `dashboard/src/App.test.tsx`
- `dashboard/src/components/alerts/AlertCard.tsx`
- `dashboard/src/components/alerts/AlertDetailPanel.tsx`
- `dashboard/src/components/sections/MonitorSection.tsx`
- `dashboard/src/lib/alerts.ts`

## Change Log

| Data | Mudança |
|---|---|
| 2026-07-26 | Story criada via BMAD CS com contexto de `epics.md`, `architecture.md` e Story 5.2 |
| 2026-07-26 | Story implementada via BMAD DS com painel inline, ações locais, toast com desfazer e testes integrados |
| 2026-07-26 | CR aplicado e Story marcada como done |

## Senior Developer Review (AI)

### Review Outcome

Approve — nenhum bloqueio restante.

### Findings

- [x] [Low] `AlertCard` inicialmente usava um `<button>` contendo blocos ricos (`dl/div`), o que é HTML frágil. Corrigido para `article role="button"` com `tabIndex`, `aria-pressed` e suporte a Enter/Espaço.

### Validation

- `npm run test` — passou, 4 arquivos / 5 testes.
- `npm run build` — passou.
- `npm run lint` — passou com 1 warning pré-existente em `dashboard/src/components/ui/button.tsx`.
- `py -m py_compile src\api\routes\predict.py tests\test_api_predict_mock.py` — passou.
