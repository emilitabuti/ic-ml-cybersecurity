/**
 * api.ts — Ponto único de acesso à FastAPI.
 *
 * ⚠️ NUNCA faça fetch direto da API em componentes React.
 *    Toda comunicação com o backend passa por este módulo.
 */
import { API_BASE_URL } from "../config";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
