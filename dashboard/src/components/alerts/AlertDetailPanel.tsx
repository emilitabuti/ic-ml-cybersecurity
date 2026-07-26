import { CheckCircle, History, RotateCcw, ShieldX } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  type DecisionStatus,
  getDecisionLabel,
  getMockAlertWindow,
  getMockTopFeatures,
} from "@/lib/alerts";
import type { PredictionResponse } from "@/types/api";

interface AlertDetailPanelProps {
  prediction: PredictionResponse;
  decisionStatus: DecisionStatus;
  onConfirm: () => void;
  onFalsePositive: () => void;
  onViewHistory: () => void;
}

export function AlertDetailPanel({
  prediction,
  decisionStatus,
  onConfirm,
  onFalsePositive,
  onViewHistory,
}: AlertDetailPanelProps) {
  const confidence = `${Math.round(prediction.confidence * 100)}%`;
  const window = getMockAlertWindow(prediction);
  const topFeatures = getMockTopFeatures(prediction);

  return (
    <section
      aria-label="Detalhe do alerta"
      className="rounded-lg border border-border bg-card p-4"
      role="region"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase text-muted-foreground">Detalhe do alerta</p>
          <h2 className="text-xl font-semibold text-card-foreground">{prediction.prediction}</h2>
        </div>
        <span className="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground">
          {getDecisionLabel(decisionStatus)}
        </span>
      </div>

      <dl className="mt-4 grid gap-3 text-sm md:grid-cols-3">
        <div>
          <dt className="text-xs text-muted-foreground">Confiança</dt>
          <dd className="font-mono font-semibold">{confidence}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Janela temporal</dt>
          <dd className="font-mono text-xs">
            {window.start} - {window.end}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Modelo</dt>
          <dd className="font-mono text-xs">{prediction.model}</dd>
        </div>
      </dl>

      <div className="mt-5">
        <h3 className="text-sm font-medium">Top 3 features motivadoras</h3>
        <div className="mt-2 grid gap-2">
          {topFeatures.map((feature) => (
            <div
              key={feature.name}
              className="grid gap-2 rounded-md border border-border px-3 py-2 text-sm sm:grid-cols-[1fr_auto_auto]"
            >
              <span className="font-mono text-xs">{feature.name}</span>
              <span className="font-mono text-xs text-muted-foreground">{feature.observedValue}</span>
              <span className="font-mono text-xs text-status-warning">{feature.deltaVsBaseline}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        <Button type="button" onClick={onConfirm}>
          <CheckCircle aria-hidden="true" />
          Confirmar
        </Button>
        <Button type="button" variant="outline" onClick={onFalsePositive}>
          <ShieldX aria-hidden="true" />
          Falso Positivo
        </Button>
        <Button type="button" variant="secondary" onClick={onViewHistory}>
          <History aria-hidden="true" />
          Ver Histórico
        </Button>
      </div>
    </section>
  );
}

interface DecisionToastProps {
  message: string;
  onUndo: () => void;
}

export function DecisionToast({ message, onUndo }: DecisionToastProps) {
  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex max-w-sm items-center gap-3 rounded-lg border border-border bg-card p-3 text-sm shadow-lg"
      role="status"
    >
      <span>{message}</span>
      <Button type="button" size="sm" variant="outline" onClick={onUndo}>
        <RotateCcw aria-hidden="true" />
        Desfazer
      </Button>
    </div>
  );
}
