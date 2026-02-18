import { create } from 'zustand';
import type { StrategySignal } from '../types/domain';

interface StrategyState {
  enabled: Record<string, boolean>;
  signals: Record<string, StrategySignal>;
  setStrategyEnabled: (id: string, enabled: boolean) => void;
  upsertSignal: (signal: StrategySignal) => void;
}

export const useStrategyStore = create<StrategyState>((set) => ({
  enabled: {},
  signals: {},
  setStrategyEnabled: (id, enabled) => set((s) => ({ enabled: { ...s.enabled, [id]: enabled } })),
  upsertSignal: (signal) =>
    set((s) => ({ signals: { ...s.signals, [`${signal.strategyId}:${signal.symbol}`]: signal } }))
}));
