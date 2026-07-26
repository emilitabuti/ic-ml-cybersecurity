import { useEffect, useMemo, useState } from "react";
import { Sidebar, type Section } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { MonitorSection } from "@/components/sections/MonitorSection";
import { PlaceholderSection } from "@/components/sections/PlaceholderSection";
import { usePredictions } from "@/hooks/usePredictions";
import { DecisionToast } from "@/components/alerts/AlertDetailPanel";
import { type DecisionStatus, getAlertId } from "@/lib/alerts";
import { severityFromPrediction } from "@/lib/severity";

const BASE_TITLE = "IC ML Cybersecurity Dashboard";

function App() {
  const [section, setSection] = useState<Section>("monitor");
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [decisions, setDecisions] = useState<Record<string, DecisionStatus>>({});
  const [toast, setToast] = useState<{
    alertId: string;
    message: string;
    previousStatus: DecisionStatus;
  } | null>(null);
  const { data: predictions = [], error, isLoading } = usePredictions();
  const activeAlerts = useMemo(
    () => predictions.filter((prediction) => severityFromPrediction(prediction) !== "safe").length,
    [predictions],
  );

  useEffect(() => {
    document.title = activeAlerts > 0 ? `(${activeAlerts}) ${BASE_TITLE}` : BASE_TITLE;

    return () => {
      document.title = BASE_TITLE;
    };
  }, [activeAlerts]);

  useEffect(() => {
    if (!toast) return;

    const timeoutId = window.setTimeout(() => setToast(null), 5_000);

    return () => window.clearTimeout(timeoutId);
  }, [toast]);

  const handleSelectAlert = (alertId: string) => {
    setSelectedAlertId(alertId);
  };

  const handleDecideAlert = (alertId: string, status: Exclude<DecisionStatus, "pending">) => {
    const previousStatus = decisions[alertId] ?? "pending";

    setDecisions((current) => ({ ...current, [alertId]: status }));
    setToast({
      alertId,
      previousStatus,
      message: status === "confirmed" ? "Alerta confirmado" : "Alerta marcado como falso positivo",
    });
  };

  const handleUndoDecision = () => {
    if (!toast) return;

    setDecisions((current) => {
      const next = { ...current };

      if (toast.previousStatus === "pending") {
        delete next[toast.alertId];
      } else {
        next[toast.alertId] = toast.previousStatus;
      }

      return next;
    });
    setToast(null);
  };

  const selectedPredictionStillExists = predictions.some((prediction) => getAlertId(prediction) === selectedAlertId);

  useEffect(() => {
    if (selectedAlertId && !selectedPredictionStillExists) {
      setSelectedAlertId(null);
    }
  }, [selectedAlertId, selectedPredictionStillExists]);

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar active={section} onSelect={setSection} />
      <div className="flex flex-1 flex-col">
        <Header metrics={{ activeAlerts, analyzedWindows: predictions.length }} />
        <main className="flex-1 overflow-auto p-6">
          {section === "monitor" && (
            <MonitorSection
              predictions={predictions}
              isLoading={isLoading}
              error={error instanceof Error ? error : null}
              selectedAlertId={selectedAlertId}
              decisions={decisions}
              onSelectAlert={handleSelectAlert}
              onDecideAlert={handleDecideAlert}
              onViewHistory={() => setSection("historico")}
            />
          )}
          {section === "alertas" && (
            <PlaceholderSection title="Alertas" story="Story 5.3 (Painel de Detalhe do Alerta)" />
          )}
          {section === "historico" && (
            <PlaceholderSection title="Histórico" story="Story 5.4 (Histórico de Alertas)" />
          )}
          {section === "modelos" && (
            <PlaceholderSection title="Modelos" story="Story 5.5 (Configuração de Threshold e Comparação de Modelos)" />
          )}
        </main>
      </div>
      {toast && <DecisionToast message={toast.message} onUndo={handleUndoDecision} />}
    </div>
  );
}

export default App;
