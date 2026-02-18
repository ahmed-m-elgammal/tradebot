import { useUiStore, type MainView } from '../../stores/uiStore';
import styles from './NavRail.module.css';

const views: MainView[] = ['COMMAND', 'POSITIONS', 'ORDERS', 'STRATEGIES', 'BACKTEST', 'RISK', 'SYSTEM'];

export function NavRail() {
  const active = useUiStore((s) => s.activeView);
  const setView = useUiStore((s) => s.setView);

  return (
    <aside className={styles.rail}>
      {views.map((view) => (
        <button key={view} className={active === view ? styles.active : ''} onClick={() => setView(view)}>{view}</button>
      ))}
    </aside>
  );
}
