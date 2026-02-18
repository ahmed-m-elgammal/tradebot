import { WebSocketManager } from '../services/wsManager';
import { toAlert, toMarketTick, toOrderEvent, toPositionSnapshot, toRiskMetrics } from '../services/streamProcessors';
import { useAlertStore } from '../stores/alertStore';
import { useMarketStore } from '../stores/marketStore';
import { useOrderStore } from '../stores/orderStore';
import { usePositionStore } from '../stores/positionStore';
import { useRiskStore } from '../stores/riskStore';

export function bootstrapStreams(): () => void {
  const ws = new WebSocketManager();
  const market = useMarketStore.getState();
  const orders = useOrderStore.getState();
  const positions = usePositionStore.getState();
  const risk = useRiskStore.getState();
  const alerts = useAlertStore.getState();

  ws.subscribe('market', (env) => market.upsertTick(toMarketTick(env as never)));
  ws.subscribe('portfolio', (env) => {
    if (env.kind === 'position_snapshot') {
      positions.setPositions(toPositionSnapshot(env as never));
      return;
    }
    const event = toOrderEvent(env as never);
    if ('orderId' in event) orders.addFill(event);
    else orders.upsertOrder(event);
  });
  ws.subscribe('system', (env) => {
    if (env.kind === 'risk_metrics') {
      risk.setMetrics(toRiskMetrics(env as never));
      return;
    }
    alerts.addAlert(toAlert(env as never));
  });

  const base = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000/ws';
  ws.connect('market', `${base}/market`);
  ws.connect('portfolio', `${base}/portfolio`);
  ws.connect('system', `${base}/system`);

  return () => ws.closeAll();
}
