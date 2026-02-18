import { useOrderStore } from '../../stores/orderStore';
import styles from './ExecutionStrip.module.css';

export function ExecutionStrip() {
  const orders = useOrderStore((s) => Object.values(s.activeOrders));
  const fills = useOrderStore((s) => s.fills.slice(0, 12));
  const pending = orders.filter((o) => o.status === 'PENDING' || o.status === 'PARTIAL').length;

  return (
    <footer className={styles.strip}>
      <div>PENDING: {pending}</div>
      <div className={styles.tape}>{fills.map((f) => <span key={`${f.orderId}-${f.ts}`}>{f.side} {f.symbol} @{f.price}</span>)}</div>
      <div>TRADES: {fills.length}</div>
    </footer>
  );
}
