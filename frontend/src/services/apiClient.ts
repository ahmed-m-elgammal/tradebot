import type { Order, Position, RiskMetrics, RiskLimitConfig } from '../types/domain';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {})
    }
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return (await res.json()) as T;
}

export const apiClient = {
  getPositions: () => request<Position[]>('/positions'),
  getOrders: () => request<Order[]>('/orders'),
  getRiskMetrics: () => request<RiskMetrics>('/risk/metrics'),
  updateRiskLimits: (limits: RiskLimitConfig) =>
    request<RiskLimitConfig>('/risk/limits', { method: 'PUT', body: JSON.stringify(limits) }),
  killSwitch: (active: boolean) => request<void>('/session/kill-switch', { method: 'POST', body: JSON.stringify({ active }) })
};
