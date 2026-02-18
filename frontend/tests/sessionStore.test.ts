import { describe, expect, it } from 'vitest';
import { useSessionStore } from '../src/stores/sessionStore';

describe('sessionStore', () => {
  it('activates kill switch via action', () => {
    useSessionStore.getState().setKillSwitch(true);
    expect(useSessionStore.getState().killSwitchActive).toBe(true);
  });
});
