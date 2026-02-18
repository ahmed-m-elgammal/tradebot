import { usePositionStore } from '../stores/positionStore';

export function usePosition(symbol: string) {
  return usePositionStore((s) => s.positions[symbol]);
}
