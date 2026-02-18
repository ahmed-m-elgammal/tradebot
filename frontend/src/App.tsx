import { useEffect } from 'react';
import { AlertsFeed } from './components/AlertsFeed/AlertsFeed';
import { ExecutionStrip } from './components/ExecutionStrip/ExecutionStrip';
import { NavRail } from './components/NavRail/NavRail';
import { RiskSentinelPanel } from './components/RiskSentinelPanel/RiskSentinelPanel';
import { StatusBar } from './components/StatusBar/StatusBar';
import { MainContent } from './components/views/MainContent';
import { bootstrapStreams } from './utils/bootstrapStreams';
import styles from './App.module.css';

export default function App() {
  useEffect(() => bootstrapStreams(), []);

  return (
    <div className={styles.layout}>
      <div className={styles.status}><StatusBar /></div>
      <div className={styles.nav}><NavRail /></div>
      <div className={styles.main}><MainContent /></div>
      <div className={styles.risk}><RiskSentinelPanel /></div>
      <div className={styles.alerts}><AlertsFeed /></div>
      <div className={styles.exec}><ExecutionStrip /></div>
    </div>
  );
}
