import { useMemo } from 'react';
import { useAlertStore } from '../stores/alertStore';
import type { AlertMessage } from '../types/domain';

export function useAlerts(severity?: AlertMessage['severity']) {
  const alerts = useAlertStore((s) => s.alerts);
  const acknowledge = useAlertStore((s) => s.acknowledge);

  const filtered = useMemo(() => {
    if (!severity) return alerts;
    return alerts.filter((a) => a.severity === severity);
  }, [alerts, severity]);

  return { alerts: filtered, acknowledge };
}
