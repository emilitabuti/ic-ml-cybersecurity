import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { apiClient } from "@/services/api";

describe("App", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    document.title = "";
  });

  it("atualiza metricas e titulo da aba com alertas ativos", async () => {
    vi.spyOn(apiClient, "getPredictionHistory").mockResolvedValue([
      {
        prediction: "DDoS",
        confidence: 0.97,
        model: "mock-cyclic-v1",
        timestamp: "2026-07-26T13:00:00Z",
      },
      {
        prediction: "Normal Traffic",
        confidence: 0.42,
        model: "mock-cyclic-v1",
        timestamp: "2026-07-26T13:00:05Z",
      },
    ]);

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("DDoS")).toBeInTheDocument();
    expect(screen.getByText("Normal Traffic")).toBeInTheDocument();

    await waitFor(() => {
      expect(document.title).toBe("(1) IC ML Cybersecurity Dashboard");
    });
    expect(apiClient.getPredictionHistory).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Alertas Ativos").nextElementSibling).toHaveTextContent("1");
    expect(screen.getByText("Janelas Analisadas").nextElementSibling).toHaveTextContent("2");
  });

  it("abre painel inline, decide alerta, desfaz por toast e acessa historico", async () => {
    vi.spyOn(apiClient, "getPredictionHistory").mockResolvedValue([
      {
        prediction: "DDoS",
        confidence: 0.97,
        model: "mock-cyclic-v1",
        timestamp: "2026-07-26T13:00:00Z",
      },
    ]);

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>,
    );

    const card = await screen.findByRole("button", { name: /abrir detalhes do alerta ddos/i });
    fireEvent.click(card);

    expect(screen.getByRole("region", { name: /detalhe do alerta/i })).toBeInTheDocument();
    expect(screen.getByText("Janela temporal")).toBeInTheDocument();
    expect(screen.getByText("Flow Duration")).toBeInTheDocument();
    expect(screen.getByText("Total Fwd Packets")).toBeInTheDocument();
    expect(screen.getByText("Fwd Packet Length Mean")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /confirmar/i }));

    expect(await screen.findAllByText("Confirmado")).toHaveLength(2);
    expect(screen.getByRole("status")).toHaveTextContent("Alerta confirmado");

    fireEvent.click(screen.getByRole("button", { name: /desfazer/i }));
    expect(screen.getAllByText("Pendente")).toHaveLength(2);

    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: /falso positivo/i }));
    expect(screen.getAllByText("Falso positivo")).toHaveLength(2);

    act(() => {
      vi.advanceTimersByTime(5_000);
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    vi.useRealTimers();

    fireEvent.click(screen.getByRole("button", { name: /ver histórico/i }));
    expect(screen.getByText(/Story 5\.4/)).toBeInTheDocument();
  });
});
