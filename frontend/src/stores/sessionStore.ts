import { create } from 'zustand';
import type { EngineState, Mode, Role } from '../types/domain';

interface SessionState {
  mode: Mode;
  engineState: EngineState;
  role: Role;
  killSwitchActive: boolean;
  sessionStartTs: number;
  equityWatermark: number;
  setMode: (mode: Mode) => void;
  setEngineState: (state: EngineState) => void;
  setRole: (role: Role) => void;
  setKillSwitch: (active: boolean) => void;
  setEquityWatermark: (value: number) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  mode: 'PAPER',
  engineState: 'PAUSED',
  role: 'READ_ONLY',
  killSwitchActive: false,
  sessionStartTs: Date.now(),
  equityWatermark: 0,
  setMode: (mode) => set({ mode }),
  setEngineState: (engineState) => set({ engineState }),
  setRole: (role) => set({ role }),
  setKillSwitch: (killSwitchActive) => set({ killSwitchActive }),
  setEquityWatermark: (equityWatermark) => set({ equityWatermark })
}));
