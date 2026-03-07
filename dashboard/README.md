# IC ML Cybersecurity — Dashboard

Interface React de monitoramento e alertas do sistema de detecção de intrusões.

## Pré-requisitos

- Node.js 18+
- npm 9+

## Instalação

```bash
cd dashboard/
npm install
cp .env.example .env
```

## Executar em desenvolvimento

```bash
npm run dev
# Acesse: http://localhost:5173
```

## Estrutura

```
dashboard/
├── src/
│   ├── config.ts        # API_BASE_URL, POLLING_INTERVAL_MS
│   ├── services/
│   │   └── api.ts       # Único ponto de acesso à FastAPI
│   ├── components/      # Componentes React reutilizáveis
│   ├── pages/           # Páginas/rotas da aplicação
│   ├── hooks/           # Custom hooks (ex: usePredictions)
│   └── main.tsx         # Entry point com QueryClientProvider
└── .env.example         # Template de variáveis de ambiente
```

## Dependências principais

| Lib | Versão | Uso |
|---|---|---|
| React + TypeScript | 18 | Base da aplicação |
| Vite | 5 | Build e HMR |
| Tailwind CSS | 3 | Estilização |
| TanStack Query | 5 | Server state + polling |
| Recharts | 2 | Gráficos |

