export interface PredictionResponse {
  prediction: string;
  confidence: number;
  model: string;
  timestamp: string;
  source_prediction?: string;
}
