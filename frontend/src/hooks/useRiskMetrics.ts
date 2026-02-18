import { useRiskStore } from '../stores/riskStore';

export function useRiskMetrics() {
  return useRiskStore((s) => s.metrics);
}
