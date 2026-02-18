import type { AlertMessage, Envelope, FillEvent, MarketTick, Order, Position, RiskMetrics } from '../types/domain';

export function toMarketTick(data: Envelope<MarketTick>): MarketTick {
  return data.payload;
}

export function toOrderEvent(data: Envelope<Order | FillEvent>): Order | FillEvent {
  return data.payload;
}

export function toPositionSnapshot(data: Envelope<Position[]>): Position[] {
  return data.payload;
}

export function toRiskMetrics(data: Envelope<RiskMetrics>): RiskMetrics {
  return data.payload;
}

export function toAlert(data: Envelope<AlertMessage>): AlertMessage {
  return data.payload;
}
