import { create } from 'zustand';
import type { MarketTick } from '../types/domain';

interface MarketState {
  prices: Record<string, MarketTick>;
  upsertTick: (tick: MarketTick) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  prices: {},
  upsertTick: (tick) => set((s) => ({ prices: { ...s.prices, [tick.symbol]: tick } }))
}));
