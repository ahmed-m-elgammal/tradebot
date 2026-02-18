# Paper Trading Milestone (Next Major Phase)

## Scope
Build a paper-trading layer that sits between strategy signals and broker/exchange adapters.

## Components
- `src/execution/order_manager.py`
  - order lifecycle states (`created -> submitted -> partially_filled -> filled/canceled/rejected`)
- `src/execution/simulated_exchange.py`
  - market + limit simulation with depth-aware partial fills
- `src/execution/position_tracker.py`
  - net position, average entry, realized/unrealized PnL
- `src/execution/reconciliation.py`
  - periodic checks: expected vs actual fills, drift, missing updates

## Risk & Controls
- Kill switch and max-loss circuit breaker
- Reject reason taxonomy and telemetry
- Exposure checks before order submission

## Observability
- Per-order structured logs
- Fill latency histograms
- Rejection/failure counters
- Daily reconciliation summary report

## Exit Criteria
- 30 consecutive paper days with no reconciliation mismatches
- All order state transitions covered by tests
- Alerting wired for stale data, fill failures, and risk halts
