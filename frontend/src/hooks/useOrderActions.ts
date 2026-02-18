import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';
import { useSessionStore } from '../stores/sessionStore';

export function useOrderActions() {
  const role = useSessionStore((s) => s.role);
  const isPermitted = role !== 'READ_ONLY';

  const killSwitchMutation = useMutation({
    mutationFn: apiClient.killSwitch
  });

  return {
    isPermitted,
    activateKillSwitch: () => (isPermitted ? killSwitchMutation.mutate(true) : undefined),
    isLoading: killSwitchMutation.isPending,
    error: killSwitchMutation.error
  };
}
