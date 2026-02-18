import { create } from 'zustand';
import type { Position } from '../types/domain';

interface PositionState {
  positions: Record<string, Position>;
  setPositions: (positions: Position[]) => void;
}

export const usePositionStore = create<PositionState>((set) => ({
  positions: {},
  setPositions: (positions) =>
    set({ positions: Object.fromEntries(positions.map((p) => [p.symbol, p])) })
}));
