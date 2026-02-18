export type Mode = 'LIVE' | 'PAPER' | 'BACKTEST';
export type EngineState = 'RUNNING' | 'PAUSED' | 'HALTED';
export type Role = 'READ_ONLY' | 'PAPER_TRADER' | 'LIVE_TRADER' | 'ADMIN';

export interface MarketTick {
  symbol: string;
  bid: number;
  ask: number;
  last: number;
  ts: number;
  sequence: number;
}

export interface Position {
  symbol: string;
  side: 'LONG' | 'SHORT';
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  sector?: string;
  cluster?: string;
}

export interface Order {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT';
  quantity: number;
  limitPrice?: number;
  status: 'PENDING' | 'PARTIAL' | 'FILLED' | 'CANCELED' | 'REJECTED';
  submittedAt: number;
}

export interface FillEvent {
  orderId: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  ts: number;
}

export interface RiskMetrics {
  drawdownPct: number;
  portfolioHeatPct: number;
  utilizationPct: number;
  concentrationPct: number;
  correlatedExposurePct: number;
  dailyLossPct: number;
}

export interface AlertMessage {
  id: string;
  ts: number;
  severity: 'CRITICAL' | 'WARN' | 'INFO';
  message: string;
  source: string;
  acknowledged: boolean;
}

export interface RiskLimitConfig {
  maxDrawdownPct: number;
  maxPortfolioHeatPct: number;
  maxPositionSizePct: number;
}

export interface StrategySignal {
  strategyId: string;
  symbol: string;
  signal: -1 | 0 | 1;
  strength: number;
  ts: number;
}

export interface Envelope<T> {
  kind: string;
  stream: 'market' | 'portfolio' | 'system';
  sequence: number;
  payload: T;
}
