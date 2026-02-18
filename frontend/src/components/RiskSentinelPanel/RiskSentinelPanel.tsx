import { useRiskMetrics } from '../../hooks/useRiskMetrics';
import { useOrderActions } from '../../hooks/useOrderActions';
import styles from './RiskSentinelPanel.module.css';

export function RiskSentinelPanel() {
  const metrics = useRiskMetrics();
  const { activateKillSwitch, isPermitted } = useOrderActions();

  return (
    <section className={styles.panel}>
      <h3>Risk Sentinel</h3>
      <p>Drawdown: {(metrics.drawdownPct * 100).toFixed(2)}%</p>
      <p>Heat: {(metrics.portfolioHeatPct * 100).toFixed(2)}%</p>
      <p>Utilization: {(metrics.utilizationPct * 100).toFixed(2)}%</p>
      <button disabled={!isPermitted} onClick={activateKillSwitch}>KILL SWITCH</button>
    </section>
  );
}
