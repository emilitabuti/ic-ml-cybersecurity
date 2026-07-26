import { useQuery } from "@tanstack/react-query";
import { POLLING_INTERVAL_MS } from "@/config";
import { apiClient } from "@/services/api";

export const PREDICTION_HISTORY_QUERY_KEY = ["predictions", "history"] as const;

export function usePredictions() {
  return useQuery({
    queryKey: PREDICTION_HISTORY_QUERY_KEY,
    queryFn: apiClient.getPredictionHistory,
    refetchInterval: POLLING_INTERVAL_MS,
  });
}
