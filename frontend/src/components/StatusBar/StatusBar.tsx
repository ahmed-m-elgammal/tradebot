import { useSessionStore } from '../../stores/sessionStore';
import { useRiskMetrics } from '../../hooks/useRiskMetrics';
import styles from './StatusBar.module.css';

export function StatusBar() {
  const mode = useSessionStore((s) => s.mode);
  const engineState = useSessionStore((s) => s.engineState);
  const killSwitch = useSessionStore((s) => s.killSwitchActive);
  const metrics = useRiskMetrics();

  return (
    <header className={`${styles.bar} ${killSwitch ? styles.killActive : ''}`}>
      <div>UTC {new Date().toISOString()}</div>
      <div>ENGINE: {engineState} | MODE: {mode}</div>
      <div>DD: {(metrics.drawdownPct * 100).toFixed(2)}%</div>
    </header>
  );
}
