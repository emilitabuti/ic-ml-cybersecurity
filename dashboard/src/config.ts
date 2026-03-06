// Configurações globais do Dashboard
// Altere VITE_API_URL no .env para apontar para outro ambiente.

export const API_BASE_URL: string =
  import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export const POLLING_INTERVAL_MS: number = 5_000;
