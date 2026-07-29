import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  Activity,
  AlertOctagon,
  CheckCircle,
  Clock,
  Database,
  Filter,
  GitBranch,
  ListChecks,
  Play,
  RadioTower,
  RotateCcw,
  ShieldCheck,
  ShieldX,
  SlidersHorizontal,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { usePredictions } from "@/hooks/usePredictions";
import { type DecisionStatus, getAlertId, getDecisionLabel } from "@/lib/alerts";
import { SEVERITY_CONFIG, severityFromPrediction, type Severity } from "@/lib/severity";
import { apiClient } from "@/services/api";
import type { PredictionResponse } from "@/types/api";

const BASE_TITLE = "IC ML Cybersecurity Dashboard";
const SEVERITIES: Severity[] = ["critical", "warning", "safe", "info"];
const DECISION_STORAGE_KEY = "ic-dashboard-alert-decisions";

const DEMO_EVENTS: PredictionResponse[] = [
  {
    prediction: "Normal Traffic",
    confidence: 0.42,
    model: "syn-flood-dashboard-demo-v1",
    timestamp: "2026-07-27T20:58:37Z",
  },
  {
    prediction: "SYN Flood - Low Intensity",
    confidence: 0.77,
    model: "syn-flood-dashboard-demo-v1",
    timestamp: "2026-07-27T20:58:38Z",
  },
  {
    prediction: "SYN Flood - Medium Intensity",
    confidence: 0.86,
    model: "syn-flood-dashboard-demo-v1",
    timestamp: "2026-07-27T20:58:38Z",
  },
  {
    prediction: "SYN Flood - High Intensity",
    confidence: 0.95,
    model: "syn-flood-dashboard-demo-v1",
    timestamp: "2026-07-27T20:58:38Z",
  },
  {
    prediction: "SYN Flood - High Intensity",
    confidence: 0.97,
    model: "syn-flood-dashboard-demo-v1",
    timestamp: "2026-07-27T20:58:39Z",
  },
];

type StatusFilter = DecisionStatus | "all";

function formatTimestamp(timestamp?: string): string {
  if (!timestamp) return "--/--/---- --:--";

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function confidenceLabel(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

function severityCounts(predictions: PredictionResponse[]): Record<Severity, number> {
  return predictions.reduce(
    (counts, prediction) => {
      counts[severityFromPrediction(prediction)] += 1;
      return counts;
    },
    { critical: 0, warning: 0, safe: 0, info: 0 } satisfies Record<Severity, number>,
  );
}

function uniqueThreatTypes(predictions: PredictionResponse[]): string[] {
  return Array.from(new Set(predictions.map((prediction) => prediction.prediction))).slice(0, 5);
}

function loadStoredDecisions(): Record<string, DecisionStatus> {
  if (typeof window === "undefined" || typeof window.localStorage?.getItem !== "function") return {};

  try {
    const raw = window.localStorage.getItem(DECISION_STORAGE_KEY);
    if (!raw) return {};

    const parsed = JSON.parse(raw) as Record<string, DecisionStatus>;
    return Object.fromEntries(
      Object.entries(parsed).filter(([, value]) => value === "confirmed" || value === "false_positive"),
    );
  } catch {
    return {};
  }
}

function DashboardCard({
  title,
  icon: Icon,
  children,
  className = "",
}: {
  title: string;
  icon: LucideIcon;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-lg border border-border bg-card p-4 shadow-sm ${className}`}>
      <h2 className="flex items-center gap-2 text-sm font-semibold text-status-info">
        <Icon className="size-4" aria-hidden="true" />
        {title}
      </h2>
      <div className="mt-3 text-sm text-card-foreground">{children}</div>
    </section>
  );
}

function SeverityList({ counts }: { counts: Record<Severity, number> }) {
  return (
    <ul className="space-y-1">
      {SEVERITIES.map((severity) => {
        const { label, colorVar, icon: Icon } = SEVERITY_CONFIG[severity];

        return (
          <li key={severity} className="flex items-center justify-between gap-3">
            <span className="inline-flex items-center gap-2" style={{ color: colorVar }}>
              <Icon className="size-3.5" aria-hidden="true" />
              {label}
            </span>
            <span className="font-mono text-card-foreground">{counts[severity]}</span>
          </li>
        );
      })}
    </ul>
  );
}

function SeverityText({ prediction }: { prediction: PredictionResponse }) {
  const severity = severityFromPrediction(prediction);
  const { label, colorVar, icon: Icon } = SEVERITY_CONFIG[severity];

  return (
    <span className="inline-flex items-center gap-1.5 font-medium" style={{ color: colorVar }}>
      <Icon className="size-3.5" aria-hidden="true" />
      {label}
    </span>
  );
}

function statusTone(status: DecisionStatus): string {
  if (status === "confirmed") return "border-status-safe/50 text-status-safe";
  if (status === "false_positive") return "border-status-warning/50 text-status-warning";
  return "border-border text-muted-foreground";
}

function App() {
  const { data: predictions = [], error, isLoading, refetch } = usePredictions();
  const [decisions, setDecisions] = useState<Record<string, DecisionStatus>>(loadStoredDecisions);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [threatFilter, setThreatFilter] = useState("all");
  const [demoSpeed, setDemoSpeed] = useState(2);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [isDemoRunning, setIsDemoRunning] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);
  const demoCancelledRef = useRef(false);
  const demoTimersRef = useRef<Array<ReturnType<typeof setTimeout>>>([]);

  const counts = useMemo(() => severityCounts(predictions), [predictions]);
  const activeAlerts = counts.critical + counts.warning + counts.info;
  const latest = predictions[0];
  const threatTypes = useMemo(() => uniqueThreatTypes(predictions), [predictions]);
  const hasSynFlood = predictions.some((prediction) => prediction.prediction.toLowerCase().includes("syn flood"));
  const treatedCount = Object.values(decisions).filter((status) => status !== "pending").length;

  const filteredHistory = useMemo(
    () =>
      predictions.filter((prediction) => {
        const alertId = getAlertId(prediction);
        const status = decisions[alertId] ?? "pending";
        const matchesStatus = statusFilter === "all" || status === statusFilter;
        const matchesThreat = threatFilter === "all" || prediction.prediction === threatFilter;

        return matchesStatus && matchesThreat;
      }),
    [decisions, predictions, statusFilter, threatFilter],
  );

  useEffect(() => {
    document.title = activeAlerts > 0 ? `(${activeAlerts}) ${BASE_TITLE}` : BASE_TITLE;

    return () => {
      document.title = BASE_TITLE;
    };
  }, [activeAlerts]);

  useEffect(() => {
    if (typeof window.localStorage?.setItem !== "function") return;

    window.localStorage.setItem(DECISION_STORAGE_KEY, JSON.stringify(decisions));
  }, [decisions]);

  useEffect(
    () => () => {
      demoCancelledRef.current = true;
      demoTimersRef.current.forEach((timer) => clearTimeout(timer));
    },
    [],
  );

  function updateDecision(prediction: PredictionResponse, status: Exclude<DecisionStatus, "pending">) {
    const alertId = getAlertId(prediction);
    setDecisions((current) => ({ ...current, [alertId]: status }));
  }

  function resetDecision(prediction: PredictionResponse) {
    const alertId = getAlertId(prediction);
    setDecisions((current) => {
      const next = { ...current };
      delete next[alertId];
      return next;
    });
  }

  function waitForDemoStep(milliseconds: number) {
    return new Promise<void>((resolve) => {
      const timer = setTimeout(resolve, milliseconds);
      demoTimersRef.current.push(timer);
    });
  }

  async function startDemoReplay() {
    if (isDemoRunning) return;

    setDemoError(null);
    setIsDemoMode(true);
    setIsDemoRunning(true);
    demoCancelledRef.current = false;
    demoTimersRef.current.forEach((timer) => clearTimeout(timer));
    demoTimersRef.current = [];

    try {
      await apiClient.clearDemoHistory();
      await refetch();

      for (const [index, event] of DEMO_EVENTS.entries()) {
        if (demoCancelledRef.current) break;

        await apiClient.pushDemoHistoryEvent({
          ...event,
          timestamp: new Date(Date.now() + index * 1_000).toISOString().replace(".000Z", "Z"),
        });
        await refetch();

        if (index < DEMO_EVENTS.length - 1) {
          await waitForDemoStep(1_600 / demoSpeed);
        }
      }
    } catch (err) {
      setDemoError(err instanceof Error ? err.message : "Falha ao iniciar modo demo.");
    } finally {
      setIsDemoRunning(false);
    }
  }

  async function clearDemoReplay() {
    demoCancelledRef.current = true;
    demoTimersRef.current.forEach((timer) => clearTimeout(timer));
    demoTimersRef.current = [];
    setIsDemoRunning(false);
    setIsDemoMode(false);
    setDemoError(null);
    await apiClient.clearDemoHistory();
    await refetch();
  }

  return (
    <main className="min-h-screen bg-background px-5 py-6 text-foreground">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="text-center">
          <h1 className="text-2xl font-semibold tracking-normal text-foreground">Visão Geral de Anomalias</h1>
          {isDemoMode && (
            <p className="mt-2 rounded-md border border-status-warning/50 bg-status-warning/10 px-3 py-2 text-sm text-status-warning">
              MODO DEMONSTRAÇÃO
            </p>
          )}
        </header>

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <DashboardCard title="Nº de Eventos" icon={AlertOctagon}>
            <p className="font-mono text-4xl font-bold">{predictions.length}</p>
            <p className="mt-1 text-muted-foreground">Janelas analisadas</p>
          </DashboardCard>

          <DashboardCard title="Tipos de Anomalia" icon={Activity}>
            {threatTypes.length > 0 ? (
              <ul className="list-disc space-y-1 pl-5">
                {threatTypes.map((type) => (
                  <li key={type}>{type}</li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground">Aguardando eventos da API</p>
            )}
          </DashboardCard>

          <DashboardCard title="Níveis de Severidade" icon={ShieldCheck}>
            <SeverityList counts={counts} />
          </DashboardCard>

          <DashboardCard title="Fonte dos Eventos" icon={Database}>
            <p>API FastAPI</p>
            <p className="mt-1 break-all font-mono text-xs text-muted-foreground">GET /history</p>
          </DashboardCard>

          <DashboardCard title="Correlação" icon={GitBranch} className="xl:col-span-2">
            <p>
              {hasSynFlood
                ? "Eventos recentes indicam sequência compatível com cenário simulado de SYN flood."
                : "Nenhuma sequência de ataque simulada identificada no histórico atual."}
            </p>
          </DashboardCard>

          <DashboardCard title="Impacto Potencial" icon={RadioTower} className="xl:col-span-2">
            <p>
              {counts.critical > 0
                ? "Alertas críticos podem indicar tentativa de indisponibilidade do serviço no cenário simulado."
                : "Sem alerta crítico no momento; o impacto potencial permanece baixo na visualização atual."}
            </p>
          </DashboardCard>

          <DashboardCard title="Horário do Evento" icon={Clock}>
            <p>Mais recente: {formatTimestamp(latest?.timestamp)}</p>
          </DashboardCard>

          <DashboardCard title="Ações Recomendadas" icon={ListChecks}>
            <ul className="list-disc space-y-1 pl-5">
              <li>Verificar severidade e confiança</li>
              <li>Comparar com o cenário simulado</li>
              <li>Registrar falso positivo se necessário</li>
            </ul>
          </DashboardCard>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Eventos Recentes</h2>

          {isLoading && (
            <div className="rounded-lg border border-border bg-card p-4">
              <LoadingSpinner />
            </div>
          )}

          {error instanceof Error && <ErrorAlert message={error.message} />}

          {!isLoading && !(error instanceof Error) && (
            <div className="overflow-hidden rounded-lg border border-border bg-card">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-status-info">
                    <th className="px-4 py-3 font-semibold">Hora</th>
                    <th className="px-4 py-3 font-semibold">Categoria</th>
                    <th className="px-4 py-3 font-semibold">Severidade</th>
                    <th className="px-4 py-3 font-semibold">Confiança</th>
                    <th className="px-4 py-3 font-semibold">Modelo</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.length === 0 && (
                    <tr>
                      <td className="px-4 py-4 text-muted-foreground" colSpan={5}>
                        Nenhum alerta recebido ainda.
                      </td>
                    </tr>
                  )}
                  {predictions.map((prediction) => (
                    <tr
                      key={`${prediction.timestamp}-${prediction.prediction}-${prediction.model}`}
                      className="border-b border-border last:border-0"
                    >
                      <td className="px-4 py-3 font-mono text-xs">{formatTimestamp(prediction.timestamp)}</td>
                      <td className="px-4 py-3 font-medium">{prediction.prediction}</td>
                      <td className="px-4 py-3">
                        <SeverityText prediction={prediction} />
                      </td>
                      <td className="px-4 py-3 font-mono">{confidenceLabel(prediction.confidence)}</td>
                      <td className="max-w-[220px] break-all px-4 py-3 font-mono text-xs text-muted-foreground">
                        {prediction.model}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-2 text-xl font-semibold">
                  <Filter className="size-5 text-status-info" aria-hidden="true" />
                  Histórico de Alertas
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {filteredHistory.length} de {predictions.length} eventos visíveis; {treatedCount} com feedback.
                </p>
              </div>
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-muted-foreground hover:border-status-info hover:text-status-info"
                onClick={() => setDecisions({})}
              >
                <RotateCcw className="size-4" aria-hidden="true" />
                Limpar feedback
              </button>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <label className="grid gap-1 text-sm">
                <span className="text-xs text-muted-foreground">Status</span>
                <select
                  className="rounded-md border border-border bg-background px-3 py-2"
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
                >
                  <option value="all">Todos</option>
                  <option value="pending">Pendentes</option>
                  <option value="confirmed">Confirmados</option>
                  <option value="false_positive">Falsos positivos</option>
                </select>
              </label>

              <label className="grid gap-1 text-sm">
                <span className="text-xs text-muted-foreground">Tipo de ameaça</span>
                <select
                  className="rounded-md border border-border bg-background px-3 py-2"
                  value={threatFilter}
                  onChange={(event) => setThreatFilter(event.target.value)}
                >
                  <option value="all">Todos</option>
                  {threatTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </label>

            </div>

            <div className="mt-4 overflow-hidden rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-status-info">
                    <th className="px-3 py-3 font-semibold">Hora</th>
                    <th className="px-3 py-3 font-semibold">Categoria</th>
                    <th className="px-3 py-3 font-semibold">Status</th>
                    <th className="px-3 py-3 font-semibold">Feedback</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredHistory.length === 0 && (
                    <tr>
                      <td className="px-3 py-4 text-muted-foreground" colSpan={4}>
                        Nenhum alerta corresponde aos filtros atuais.
                      </td>
                    </tr>
                  )}
                  {filteredHistory.map((prediction) => {
                    const alertId = getAlertId(prediction);
                    const decisionStatus = decisions[alertId] ?? "pending";

                    return (
                      <tr key={alertId} className="border-b border-border last:border-0">
                        <td className="px-3 py-3 font-mono text-xs">{formatTimestamp(prediction.timestamp)}</td>
                        <td className="px-3 py-3">
                          <div className="font-medium">{prediction.prediction}</div>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            <SeverityText prediction={prediction} />
                            <span className="font-mono">{confidenceLabel(prediction.confidence)}</span>
                          </div>
                        </td>
                        <td className="px-3 py-3">
                          <span className={`rounded-md border px-2 py-1 text-xs ${statusTone(decisionStatus)}`}>
                            {getDecisionLabel(decisionStatus)}
                          </span>
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              className="inline-flex items-center gap-1 rounded-md border border-status-safe/50 px-2 py-1 text-xs text-status-safe hover:bg-status-safe/10"
                              onClick={() => updateDecision(prediction, "confirmed")}
                            >
                              <CheckCircle className="size-3.5" aria-hidden="true" />
                              Confirmar
                            </button>
                            <button
                              type="button"
                              className="inline-flex items-center gap-1 rounded-md border border-status-warning/50 px-2 py-1 text-xs text-status-warning hover:bg-status-warning/10"
                              onClick={() => updateDecision(prediction, "false_positive")}
                            >
                              <ShieldX className="size-3.5" aria-hidden="true" />
                              Falso positivo
                            </button>
                            {decisionStatus !== "pending" && (
                              <button
                                type="button"
                                className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:text-card-foreground"
                                onClick={() => resetDecision(prediction)}
                              >
                                <Trash2 className="size-3.5" aria-hidden="true" />
                                Resetar
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <aside className="rounded-lg border border-border bg-card p-4">
            <h2 className="flex items-center gap-2 text-xl font-semibold">
              <SlidersHorizontal className="size-5 text-status-info" aria-hidden="true" />
              Modo Demo
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Reproduz a sequência usada na avaliação SYN flood diretamente pelo endpoint POST /history/demo.
            </p>

            <label className="mt-4 grid gap-1 text-sm">
              <span className="text-xs text-muted-foreground">Velocidade</span>
              <select
                className="rounded-md border border-border bg-background px-3 py-2"
                value={demoSpeed}
                onChange={(event) => setDemoSpeed(Number(event.target.value))}
                disabled={isDemoRunning}
              >
                <option value={1}>1x</option>
                <option value={2}>2x</option>
                <option value={4}>4x</option>
              </select>
            </label>

            <div className="mt-4 grid gap-2">
              <button
                type="button"
                className="inline-flex items-center justify-center gap-2 rounded-md bg-status-info px-3 py-2 text-sm font-medium text-background disabled:cursor-not-allowed disabled:opacity-60"
                onClick={startDemoReplay}
                disabled={isDemoRunning}
              >
                <Play className="size-4" aria-hidden="true" />
                {isDemoRunning ? "Reproduzindo..." : "Iniciar demo"}
              </button>
              <button
                type="button"
                className="inline-flex items-center justify-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-muted-foreground hover:text-card-foreground"
                onClick={() => {
                  void clearDemoReplay();
                }}
              >
                <Trash2 className="size-4" aria-hidden="true" />
                Limpar demo
              </button>
            </div>

            {demoError && <p className="mt-3 text-sm text-status-critical">{demoError}</p>}
          </aside>
        </section>

        <footer className="text-right text-xs text-muted-foreground">
          Última atualização: {formatTimestamp(new Date().toISOString())}
        </footer>
      </div>
    </main>
  );
}

export default App;
