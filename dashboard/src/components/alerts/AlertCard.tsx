import { Activity, Clock, Cpu, Percent } from "lucide-react";
import type { KeyboardEvent } from "react";
import { SeverityBadge } from "@/components/alerts/SeverityBadge";
import { type DecisionStatus, getDecisionLabel } from "@/lib/alerts";
import { cn } from "@/lib/utils";
import { severityFromPrediction } from "@/lib/severity";
import type { PredictionResponse } from "@/types/api";

interface AlertCardProps {
  prediction: PredictionResponse;
  decisionStatus?: DecisionStatus;
  isSelected?: boolean;
  onSelect?: () => void;
  className?: string;
}

export function AlertCard({
  prediction,
  decisionStatus = "pending",
  isSelected = false,
  onSelect,
  className,
}: AlertCardProps) {
  const severity = severityFromPrediction(prediction);
  const confidence = `${Math.round(prediction.confidence * 100)}%`;
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect?.();
    }
  };

  return (
    <article
      aria-label={`Abrir detalhes do alerta ${prediction.prediction}`}
      aria-pressed={isSelected}
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={handleKeyDown}
      className={cn(
        "w-full rounded-lg border border-border bg-card p-4 text-left transition-colors",
        "hover:border-status-info/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        isSelected && "border-status-info/70",
        decisionStatus === "confirmed" && "border-status-safe/60 bg-status-safe/5",
        decisionStatus === "false_positive" && "border-status-warning/60 bg-status-warning/5",
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-xs uppercase text-muted-foreground">
            <Activity className="size-3.5" aria-hidden="true" />
            Tipo de ameaça
          </p>
          <h2 className="mt-1 truncate text-lg font-semibold text-card-foreground">{prediction.prediction}</h2>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <span className="rounded-md border border-border px-2 py-0.5 text-xs text-muted-foreground">
            {getDecisionLabel(decisionStatus)}
          </span>
          <SeverityBadge severity={severity} />
        </div>
      </div>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Percent className="size-3.5" aria-hidden="true" />
            Confiança
          </dt>
          <dd className="font-mono font-semibold">{confidence}</dd>
        </div>
        <div>
          <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="size-3.5" aria-hidden="true" />
            Timestamp
          </dt>
          <dd className="break-all font-mono text-xs">{prediction.timestamp}</dd>
        </div>
        <div>
          <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Cpu className="size-3.5" aria-hidden="true" />
            Modelo
          </dt>
          <dd className="break-all font-mono text-xs">{prediction.model}</dd>
        </div>
      </dl>
    </article>
  );
}
