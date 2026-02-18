import { z } from 'zod';
import type { Envelope } from '../types/domain';

const envelopeSchema = z.object({
  kind: z.string(),
  stream: z.enum(['market', 'portfolio', 'system']),
  sequence: z.number().int().nonnegative(),
  payload: z.unknown()
});

type Handler = (envelope: Envelope<unknown>) => void;
type GapHandler = (stream: string, expected: number, got: number) => void;

export class WebSocketManager {
  private sockets = new Map<string, WebSocket>();
  private handlers = new Map<string, Handler[]>();
  private lastSeq = new Map<string, number>();
  private gapHandler?: GapHandler;

  onGapDetected(handler: GapHandler): void {
    this.gapHandler = handler;
  }

  subscribe(stream: string, handler: Handler): () => void {
    const next = [...(this.handlers.get(stream) ?? []), handler];
    this.handlers.set(stream, next);
    return () => this.handlers.set(stream, (this.handlers.get(stream) ?? []).filter((h) => h !== handler));
  }

  connect(stream: 'market' | 'portfolio' | 'system', url: string): void {
    const ws = new WebSocket(url);
    ws.onmessage = (event) => this.handleMessage(stream, event.data);
    this.sockets.set(stream, ws);
  }

  closeAll(): void {
    this.sockets.forEach((ws) => ws.close());
    this.sockets.clear();
  }

  private handleMessage(stream: string, raw: unknown): void {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
    const validated = envelopeSchema.safeParse(parsed);
    if (!validated.success) return;

    const env = validated.data as Envelope<unknown>;
    const prev = this.lastSeq.get(stream);
    const expected = (prev ?? env.sequence - 1) + 1;
    if (env.sequence !== expected && this.gapHandler) this.gapHandler(stream, expected, env.sequence);
    this.lastSeq.set(stream, env.sequence);

    for (const handler of this.handlers.get(stream) ?? []) handler(env);
  }
}
