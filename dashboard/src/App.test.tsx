import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { apiClient } from "@/services/api";

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
}

describe("App", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.title = "";
  });

  it("exibe a visao geral consumindo o historico atual da API", async () => {
    vi.spyOn(apiClient, "getPredictionHistory").mockResolvedValue([
      {
        prediction: "SYN Flood - High Intensity",
        confidence: 0.97,
        model: "syn-flood-dashboard-demo-v1",
        timestamp: "2026-07-26T13:00:00Z",
      },
      {
        prediction: "Normal Traffic",
        confidence: 0.42,
        model: "syn-flood-dashboard-demo-v1",
        timestamp: "2026-07-26T13:00:05Z",
      },
    ]);

    renderApp();

    expect(await screen.findByRole("heading", { name: /anomalias/i })).toBeInTheDocument();
    expect(screen.getByText("Nº de Eventos")).toBeInTheDocument();
    expect(screen.getByText("Tipos de Anomalia")).toBeInTheDocument();
    expect(screen.getByText(/Severidade/)).toBeInTheDocument();
    expect(screen.getByText("Fonte dos Eventos")).toBeInTheDocument();
    expect(screen.getByText("GET /history")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Historico|Histórico/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Modo Demo" })).toBeInTheDocument();

    expect((await screen.findAllByText("SYN Flood - High Intensity")).length).toBeGreaterThanOrEqual(2);

    const table = screen.getAllByRole("table")[0];
    expect(within(table).getByText("SYN Flood - High Intensity")).toBeInTheDocument();
    expect(within(table).getByText("Normal Traffic")).toBeInTheDocument();
    expect(within(table).getByText("97%")).toBeInTheDocument();
    expect(within(table).getByText("42%")).toBeInTheDocument();

    await waitFor(() => {
      expect(document.title).toBe("(1) IC ML Cybersecurity Dashboard");
    });
    expect(apiClient.getPredictionHistory).toHaveBeenCalledTimes(1);
  });

  it("permite registrar feedback local no historico", async () => {
    vi.spyOn(apiClient, "getPredictionHistory").mockResolvedValue([
      {
        prediction: "SYN Flood - High Intensity",
        confidence: 0.97,
        model: "syn-flood-dashboard-demo-v1",
        timestamp: "2026-07-26T13:00:00Z",
      },
    ]);

    renderApp();

    expect(await screen.findByRole("heading", { name: /Historico|Histórico/i })).toBeInTheDocument();
    await screen.findAllByText("SYN Flood - High Intensity");

    fireEvent.click(screen.getByRole("button", { name: /Confirmar/i }));

    expect(screen.getByText("Confirmado")).toBeInTheDocument();
  });

  it("renderiza historico e demo sem placeholders de construcao", async () => {
    vi.spyOn(apiClient, "getPredictionHistory").mockResolvedValue([]);

    renderApp();

    expect(await screen.findByText("Nenhum alerta recebido ainda.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Historico|Histórico/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Modo Demo" })).toBeInTheDocument();
    expect(screen.queryByText(/Em construcao|Em construção/i)).not.toBeInTheDocument();
  });
});
