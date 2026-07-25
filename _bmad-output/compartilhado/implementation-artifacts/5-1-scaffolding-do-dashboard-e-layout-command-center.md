# Story 5.1: Scaffolding do Dashboard e Layout Command Center

Status: done

## Story

Como desenvolvedora do dashboard (Isabela),
Quero o layout base do dashboard com sidebar fixa, header de métricas e tema escuro configurado,
Para que todas as histórias seguintes tenham uma estrutura visual consistente para construir.

## Acceptance Criteria

**Dado** que o projeto `dashboard/` está scaffoldado (Story 1.1)
**Quando** executo `npm run dev` e abro `http://localhost:5173`
**Então** a interface exibe sidebar fixa (220px) com 4 seções: Monitor, Alertas, Histórico, Modelos
**E** o tema escuro está ativo com `bg-base: #0F1117` como fundo principal
**E** o header exibe 4 cards de métricas: alertas ativos, janelas analisadas, precisão do modelo e latência
**E** as fontes Inter (interface) e JetBrains Mono (dados técnicos) estão aplicadas
**E** nenhum dado pessoal ou sensível é processado — apenas dados simulados/públicos (NFR12)

## Tasks / Subtasks

- [x] Task 1: Ativar tema escuro e tokens de cor do Command Center (AC: tema escuro, `bg-base`)
  - [x] Subtask 1.1: `class="dark"` fixa em `<html>` (`dashboard/index.html`), `lang="pt-BR"`, título atualizado
  - [x] Subtask 1.2: Sobrescrever `--background` do bloco `.dark` em `src/index.css` para `#0F1117`
  - [x] Subtask 1.3: Adicionar tokens semânticos de severidade (`--status-critical/warning/safe/info`) e expor via `tailwind.config.js` (`colors.status.*`)
- [x] Task 2: Instalar e aplicar fontes Inter e JetBrains Mono (AC: fontes)
  - [x] Subtask 2.1: `npm install @fontsource-variable/inter @fontsource-variable/jetbrains-mono`, remover `@fontsource-variable/geist` (não usado no design oficial)
  - [x] Subtask 2.2: Atualizar `fontFamily.sans`/`fontFamily.mono` em `tailwind.config.js` e `--font-sans`/`--font-mono` em `src/index.css`
- [x] Task 3: Implementar Sidebar fixa de 220px com as 4 seções (AC: sidebar)
  - [x] Subtask 3.1: `src/components/layout/Sidebar.tsx` — navegação por estado local (`useState`), sem router (evita dependência desnecessária)
- [x] Task 4: Implementar Header com os 4 cards de métrica (AC: header)
  - [x] Subtask 4.1: `src/components/cards/MetricCard.tsx` (componente genérico reutilizável)
  - [x] Subtask 4.2: `src/components/layout/Header.tsx` com os 4 cards (alertas ativos, janelas analisadas, precisão, latência) — valores placeholder (`—`), integração real é da Story 5.2
- [x] Task 5: Montar o `AppShell` em `src/App.tsx` (Sidebar + Header + conteúdo por seção)
  - [x] Subtask 5.1: Seções `Alertas`/`Histórico`/`Modelos` como placeholders explícitos referenciando as stories que as implementarão (5.3/5.4/5.5)
  - [x] Subtask 5.2: Seção `Monitor` com legenda de severidade + tabela de eventos recentes (placeholder de dados)
- [x] Task 6: Reaproveitar conceitos do protótipo isolado de Isabela (`Isa252-patch-1`, não mesclada)
  - [x] Subtask 6.1: `src/lib/severity.ts` — mapeamento severidade → cor/ícone/label, inspirado na função `classBySeverity()` do protótipo Flask/JS, adaptado à paleta oficial (critical/warning/safe/info)
  - [x] Subtask 6.2: `src/components/alerts/SeverityBadge.tsx` — badge cor + ícone + label (nunca só cor, WCAG AA)
  - [x] Subtask 6.3: `src/components/alerts/RecentEventsTable.tsx` — estrutura de tabela inspirada em "Eventos Recentes" do protótipo (colunas Hora/Categoria/Severidade), sem o campo `Origem` (não portável — ver nota de reconciliação em `epics.md`, Epic 5)
- [x] Task 7: Validar build e lint
  - [x] Subtask 7.1: `npm run build` (tsc -b && vite build) sem erros
  - [x] Subtask 7.2: `npm run lint` sem novos erros (1 warning pré-existente em `button.tsx`, não relacionado a esta story)

## Dev Notes

### Decisão arquitetural mantida

Conforme `architecture.md` (ADR: "banco de dados formal está fora do escopo desta IC") e a nota de reconciliação em `epics.md` (Epic 5), a stack oficial (Vite + React + TS + Tailwind + shadcn + TanStack Query, sem banco de dados) foi mantida integralmente. O protótipo Flask + MySQL de Isabela (branch `Isa252-patch-1`) **não foi mesclado nem seu código reaproveitado literalmente** — apenas os conceitos de UI/UX validados de forma independente (classificação de severidade, cards de resumo, tabela de eventos) foram extraídos e reimplementados em React/TypeScript sobre a arquitetura oficial.

### Arquivos criados/modificados

```
dashboard/
├── index.html                              ← class="dark", lang="pt-BR", título
├── tailwind.config.js                      ← colors.status.*, fontFamily.sans/mono
├── src/
│   ├── index.css                           ← --background dark = #0F1117, --status-*, fontes
│   ├── App.tsx                             ← reescrito: AppShell (Sidebar + Header + seções)
│   ├── lib/severity.ts                     ← NOVO — mapeamento severidade
│   ├── components/
│   │   ├── layout/Sidebar.tsx              ← NOVO
│   │   ├── layout/Header.tsx               ← NOVO
│   │   ├── cards/MetricCard.tsx            ← NOVO
│   │   ├── alerts/SeverityBadge.tsx        ← NOVO
│   │   ├── alerts/RecentEventsTable.tsx    ← NOVO (dados placeholder — Story 5.2 conecta à API)
│   │   └── sections/
│   │       ├── MonitorSection.tsx          ← NOVO
│   │       └── PlaceholderSection.tsx      ← NOVO
│   └── App.css                             ← REMOVIDO (não usado após reescrita do App.tsx)
```

### Próximos passos (fora do escopo desta story)

- Story 5.2 substitui os valores placeholder do Header e o mock de `RecentEventsTable` por dados reais via polling (`GET /history`, `GET /model/info`).
- Story 4.4 (`POST /predict/mock`) é o bloqueador oficial para a Story 5.2 — ver `epics.md`.

## Change Log

| Data | Mudança |
|---|---|
| 2026-07-25 | Story implementada — layout Command Center completo, conceitos de UI do protótipo de Isabela reaproveitados |
