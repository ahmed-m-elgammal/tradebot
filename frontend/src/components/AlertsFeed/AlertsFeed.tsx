import { useAlerts } from '../../hooks/useAlerts';
import styles from './AlertsFeed.module.css';

export function AlertsFeed() {
  const { alerts, acknowledge } = useAlerts();

  return (
    <section className={styles.feed}>
      <h3>Alerts</h3>
      <ul>
        {alerts.slice(0, 20).map((alert) => (
          <li key={alert.id} className={styles[alert.severity.toLowerCase()]}> 
            <span>{new Date(alert.ts).toLocaleTimeString()} {alert.severity}</span>
            <p>{alert.message}</p>
            {!alert.acknowledged && <button onClick={() => acknowledge(alert.id)}>Acknowledge</button>}
          </li>
        ))}
      </ul>
    </section>
  );
}
