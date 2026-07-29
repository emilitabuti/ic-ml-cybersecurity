import { AlertCard } from "@/components/alerts/AlertCard";
import { AlertDetailPanel } from "@/components/alerts/AlertDetailPanel";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { type DecisionStatus, getAlertId } from "@/lib/alerts";
import { SEVERITY_CONFIG, type Severity } from "@/lib/severity";
import type { PredictionResponse } from "@/types/api";

const SEVERITIES: Severity[] = ["critical", "warning", "info", "safe"];

interface MonitorSectionProps {
  predictions: PredictionResponse[];
  isLoading: boolean;
  error: Error | null;
  selectedAlertId: string | null;
  decisions: Record<string, DecisionStatus>;
  onSelectAlert: (alertId: string) => void;
  onDecideAlert: (alertId: string, status: Exclude<DecisionStatus, "pending">) => void;
  onViewHistory: () => void;
}

export function MonitorSection({
  predictions,
  isLoading,
  error,
  selectedAlertId,
  decisions,
  onSelectAlert,
  onDecideAlert,
  onViewHistory,
}: MonitorSectionProps) {
  const isError = error !== null;
  const selectedPrediction = predictions.find((prediction) => getAlertId(prediction) === selectedAlertId);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span>Legenda de severidade:</span>
        {SEVERITIES.map((severity) => {
          const { label, colorVar, icon: Icon } = SEVERITY_CONFIG[severity];
          return (
            <span key={severity} className="inline-flex items-center gap-1" style={{ color: colorVar }}>
              <Icon className="size-3.5" aria-hidden="true" />
              {label}
            </span>
          );
        })}
      </div>

      {isLoading && <LoadingSpinner />}
      {isError && <ErrorAlert message={error.message} />}
      {!isLoading && !isError && predictions.length === 0 && (
        <div className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
          Nenhum alerta recebido ainda.
        </div>
      )}
      {!isLoading && !isError && predictions.length > 0 && (
        <div className="grid gap-3 xl:grid-cols-2">
          {predictions.map((prediction) => {
            const alertId = getAlertId(prediction);

            return (
              <AlertCard
                key={alertId}
                prediction={prediction}
                decisionStatus={decisions[alertId] ?? "pending"}
                isSelected={selectedAlertId === alertId}
                onSelect={() => onSelectAlert(alertId)}
              />
            );
          })}
        </div>
      )}
      {selectedPrediction && selectedAlertId && (
        <AlertDetailPanel
          prediction={selectedPrediction}
          decisionStatus={decisions[selectedAlertId] ?? "pending"}
          onConfirm={() => onDecideAlert(selectedAlertId, "confirmed")}
          onFalsePositive={() => onDecideAlert(selectedAlertId, "false_positive")}
          onViewHistory={onViewHistory}
        />
      )}
    </div>
  );
}
