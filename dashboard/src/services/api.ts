/**
 * api.ts — Ponto único de acesso à FastAPI.
 *
 * ⚠️ NUNCA faça fetch direto da API em componentes React.
 *    Toda comunicação com o backend passa por este módulo.
 */
import { API_BASE_URL } from "../config";
import type { PredictionResponse } from "@/types/api";

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

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getPredictionHistory: () => request<PredictionResponse[]>("/history"),
};

export const api = apiClient;
