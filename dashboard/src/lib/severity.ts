/**
 * severity.ts — Mapeamento de severidade de alertas
 * Severidade NUNCA é comunicada apenas por cor — sempre cor + ícone + label textual
 */
import { AlertOctagon, AlertTriangle, ShieldCheck, Info, type LucideIcon } from "lucide-react";
import type { PredictionResponse } from "@/types/api";

export type Severity = "critical" | "warning" | "safe" | "info";

interface SeverityConfig {
  label: string;
  colorVar: string;
  icon: LucideIcon;
}

export const SEVERITY_CONFIG: Record<Severity, SeverityConfig> = {
  critical: { label: "Crítico", colorVar: "var(--status-critical)", icon: AlertOctagon },
  warning: { label: "Suspeito", colorVar: "var(--status-warning)", icon: AlertTriangle },
  safe: { label: "Seguro", colorVar: "var(--status-safe)", icon: ShieldCheck },
  info: { label: "Informativo", colorVar: "var(--status-info)", icon: Info },
};

/** Deriva a severidade a partir do nível de confiança do modelo (0-1). */
export function severityFromConfidence(confidence: number): Severity {
  if (confidence >= 0.9) return "critical";
  if (confidence >= 0.7) return "warning";
  if (confidence >= 0.4) return "info";
  return "safe";
}

export function severityFromPrediction(prediction: PredictionResponse): Severity {
  const label = prediction.prediction.toLowerCase();
  if (label.includes("normal") || label.includes("benign")) return "safe";
  return severityFromConfidence(prediction.confidence);
}
