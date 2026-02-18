import { describe, expect, it, vi } from 'vitest';
import { WebSocketManager } from '../src/services/wsManager';

describe('WebSocketManager', () => {
  it('detects sequence gaps', () => {
    const manager = new WebSocketManager();
    const gapSpy = vi.fn();
    manager.onGapDetected(gapSpy);

    const handler = (manager as unknown as { handleMessage: (s: string, raw: unknown) => void }).handleMessage;
    handler.call(manager, 'market', JSON.stringify({ kind: 'tick', stream: 'market', sequence: 1, payload: {} }));
    handler.call(manager, 'market', JSON.stringify({ kind: 'tick', stream: 'market', sequence: 3, payload: {} }));

    expect(gapSpy).toHaveBeenCalledWith('market', 2, 3);
  });
});
