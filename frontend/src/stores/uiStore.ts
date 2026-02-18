import { create } from 'zustand';

export type MainView = 'COMMAND' | 'POSITIONS' | 'ORDERS' | 'STRATEGIES' | 'BACKTEST' | 'RISK' | 'SYSTEM';

interface UiState {
  activeView: MainView;
  range: '1H' | '1D' | '1W' | '1M' | 'ALL';
  panelCollapsed: Record<string, boolean>;
  setView: (view: MainView) => void;
  setRange: (range: UiState['range']) => void;
  togglePanel: (panel: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeView: 'COMMAND',
  range: '1D',
  panelCollapsed: {},
  setView: (activeView) => set({ activeView }),
  setRange: (range) => set({ range }),
  togglePanel: (panel) => set((s) => ({ panelCollapsed: { ...s.panelCollapsed, [panel]: !s.panelCollapsed[panel] } }))
}));
