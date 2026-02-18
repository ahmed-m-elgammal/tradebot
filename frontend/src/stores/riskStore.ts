import { create } from 'zustand';
import type { AlertMessage, RiskLimitConfig, RiskMetrics } from '../types/domain';

interface RiskState {
  metrics: RiskMetrics;
  limits: RiskLimitConfig;
  breaches: AlertMessage[];
  setMetrics: (metrics: RiskMetrics) => void;
  setLimits: (limits: RiskLimitConfig) => void;
  addBreach: (alert: AlertMessage) => void;
}

export const useRiskStore = create<RiskState>((set) => ({
  metrics: {
    drawdownPct: 0,
    portfolioHeatPct: 0,
    utilizationPct: 0,
    concentrationPct: 0,
    correlatedExposurePct: 0,
    dailyLossPct: 0
  },
  limits: {
    maxDrawdownPct: 0.12,
    maxPortfolioHeatPct: 0.2,
    maxPositionSizePct: 0.05
  },
  breaches: [],
  setMetrics: (metrics) => set({ metrics }),
  setLimits: (limits) => set({ limits }),
  addBreach: (alert) => set((s) => ({ breaches: [alert, ...s.breaches].slice(0, 500) }))
}));
