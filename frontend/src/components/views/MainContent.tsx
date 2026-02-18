import { useUiStore } from '../../stores/uiStore';
import styles from './MainContent.module.css';

export function MainContent() {
  const activeView = useUiStore((s) => s.activeView);
  return (
    <main className={styles.main}>
      <h2>{activeView}</h2>
      <p>Panel implementation scaffolded. Wire each zone to hooks/services incrementally.</p>
    </main>
  );
}
