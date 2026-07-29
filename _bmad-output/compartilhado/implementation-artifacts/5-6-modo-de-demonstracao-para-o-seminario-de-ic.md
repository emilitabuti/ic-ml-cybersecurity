# Story 5.6: Modo de Demonstracao para o Seminario de IC

> **Status: concluida** (2026-07-29) — Implementado modo demo de um clique no dashboard, baseado no cenario SYN flood usado no relatorio parcial revisado.

## Story

Como pesquisadora,
quero reproduzir uma sessao historica de alertas em velocidade controlada,
para apresentar o sistema funcionando ao vivo sem depender de trafego real.

## Implementacao

- `dashboard/src/App.tsx`
  - Nova area "Modo Demo".
  - Botao "Iniciar demo" injeta uma sequencia de cinco eventos:
    - trafego normal;
    - SYN flood de baixa intensidade;
    - SYN flood de media intensidade;
    - dois SYN floods de alta intensidade.
  - Velocidades disponiveis: 1x, 2x e 4x.
  - Banner "MODO DEMONSTRACAO" durante a sessao.
  - Botao "Limpar demo" remove eventos de demonstracao da API.

- `dashboard/src/services/api.ts`
  - `pushDemoHistoryEvent()` para `POST /history/demo`.
  - `clearDemoHistory()` para `DELETE /history/demo`.

- `dashboard/src/services/api.test.ts`
  - Testes para POST e DELETE de demonstracao.

## Observacoes

- A story usa os endpoints de demonstracao ja existentes na FastAPI.
- O fluxo preserva a seguranca metodologica do relatorio: nao executa ataque real e nao depende de rede externa.
- Os timestamps sao renovados durante a reproducao para que a sessao se comporte como tempo quase real.

## Validacao

- `npm test` em `dashboard/`: 8 testes passaram.
- `npm run build` em `dashboard/`: build concluido com sucesso.
