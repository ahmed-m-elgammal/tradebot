import { create } from 'zustand';
import type { AlertMessage } from '../types/domain';

interface AlertState {
  alerts: AlertMessage[];
  addAlert: (alert: AlertMessage) => void;
  acknowledge: (id: string) => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  alerts: [],
  addAlert: (alert) => set((s) => ({ alerts: [alert, ...s.alerts].slice(0, 5000) })),
  acknowledge: (id) => set((s) => ({ alerts: s.alerts.map((a) => (a.id === id ? { ...a, acknowledged: true } : a)) }))
}));
