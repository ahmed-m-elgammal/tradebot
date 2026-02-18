# Trading Bot Operator UI (React + Vite + TypeScript)

This frontend implements the requested technical architecture baseline:

- React 18 + Vite + strict TypeScript
- Layered architecture: `types -> services -> stores -> hooks -> components`
- Zustand for operator/live domain state
- TanStack Query for API mutation/query concerns
- WebSocket manager outside React tree with sequencing + gap detection
- CSS Modules + CSS custom properties

## Structure

- `src/types/`: shared domain contracts
- `src/services/`: API client, websocket manager, stream processors
- `src/stores/`: domain stores (`market`, `order`, `position`, `risk`, `strategy`, `session`, `alert`, `ui`)
- `src/hooks/`: component-facing orchestrators/selectors
- `src/components/`: zone-based components matching command center layout

## Commands

```bash
npm install
npm run typecheck
npm run test
npm run build
npm run dev
```
