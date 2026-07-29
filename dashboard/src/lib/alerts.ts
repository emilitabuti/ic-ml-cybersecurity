import type { PredictionResponse } from "@/types/api";

export type DecisionStatus = "pending" | "confirmed" | "false_positive";

export interface TrafficFeature {
  name: string;
  observedValue: string;
  deltaVsBaseline: string;
}

export interface AlertWindow {
  start: string;
  end: string;
}

export function getAlertId(prediction: PredictionResponse): string {
  return `${prediction.timestamp}-${prediction.source_prediction ?? prediction.prediction}-${prediction.prediction}-${prediction.model}`;
}

export function getDecisionLabel(status: DecisionStatus): string {
  if (status === "confirmed") return "Confirmado";
  if (status === "false_positive") return "Falso positivo";
  return "Pendente";
}

export function getMockAlertWindow(prediction: PredictionResponse): AlertWindow {
  const end = new Date(prediction.timestamp);

  if (Number.isNaN(end.getTime())) {
    return { start: prediction.timestamp, end: prediction.timestamp };
  }

  const start = new Date(end.getTime() - 5_000);

  return {
    start: start.toISOString().replace(".000Z", "Z"),
    end: prediction.timestamp,
  };
}

export function getMockTopFeatures(prediction: PredictionResponse): TrafficFeature[] {
  const multiplier = Math.round(prediction.confidence * 100);

  return [
    {
      name: "Flow Duration",
      observedValue: `${multiplier * 120} ms`,
      deltaVsBaseline: `+${Math.max(multiplier - 42, 1)}%`,
    },
    {
      name: "Total Fwd Packets",
      observedValue: String(Math.max(Math.round(multiplier / 3), 1)),
      deltaVsBaseline: `+${Math.max(multiplier - 55, 1)}%`,
    },
    {
      name: "Fwd Packet Length Mean",
      observedValue: `${Math.max(multiplier * 6, 1)} bytes`,
      deltaVsBaseline: `+${Math.max(multiplier - 61, 1)}%`,
    },
  ];
}
