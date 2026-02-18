# Trading Bot UI — Full Structure Plan

This document captures the full operator-grade dashboard blueprint for the trading bot UI. The design target is a **single-screen command center** where critical risk and execution controls are always visible.

## 1) Overall Layout Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│  GLOBAL STATUS BAR  (always visible, always live)                 │
├──────────┬────────────────────────────┬──────────────────┬──────────┤
│          │                            │                  │          │
│  NAV     │   MAIN CONTENT AREA        │  RISK SENTINEL   │  ALERTS  │
│  RAIL    │   (context-swappable)      │  PANEL           │  FEED    │
│          │                            │  (fixed right)   │          │
├──────────┴────────────────────────────┴──────────────────┤          │
│  EXECUTION STRIP  (live orders + fills, always visible) │          │
└──────────────────────────────────────────────────────────┴──────────┘
```

Critical invariant:

- The **Risk Sentinel Panel** and **Alerts Feed** are fixed and visible regardless of main view context.

## 2) Functional Zones

### Zone 1 — Global Status Bar

Top, full-width, always visible; serves as system heartbeat.

- **Left**: UTC clock, feed connectivity + latency, strategy engine state, operating mode badge.
- **Center**: realized/unrealized P&L, equity, peak watermark, drawdown state coloring.
- **Right**: emergency kill switch (press + hold), pause-all action, session timer.

### Zone 2 — Navigation Rail

Left vertical rail with icon + label destinations.

1. Command
2. Positions
3. Orders
4. Strategies
5. Backtest
6. Risk
7. System

Each destination includes a live badge count/health indicator.

### Zone 3 — Main Content Area

Context-swappable center pane with dedicated screens:

- **Command**: KPI row, equity curve, summarized positions/fills panels.
- **Positions**: full position table, exposure heatmap, detail drawer.
- **Orders**: live book, full history, fill tape, manual order entry.
- **Strategies**: roster, live signals, parameter controls, walk-forward panel.
- **Backtest**: config, results, comparison/history.
- **Risk**: editable limits + utilization + breach timeline.

### Zone 4 — Risk Sentinel Panel

Fixed right panel (always visible), includes:

- Drawdown gauge
- Live risk metric stack (heat/utilization/concentration/correlation/daily loss)
- Kill switch controls (armed/active + resume workflow)
- Last-five risk event log

### Zone 5 — Execution Strip

Bottom full-width strip; always visible.

- Pending order count
- Live fill tape pills (latest fills)
- Session trade count + fill-rate metric
- Click-through into Orders view

### Zone 6 — Alerts Feed

Far-right fixed column for persistent session alerts.

- Severity lanes: CRITICAL / WARN / INFO with distinct visual treatment.
- Each item includes timestamp, severity, message, source.
- Acknowledge + unread management.
- Mute/info filter/export controls.

## 3) Live Data Stream Model

### Loop 1 — Price Tick Stream (100–700ms)

WebSocket push updates:

- Position-level and aggregate unrealized P&L
- Limit trigger distance
- Signal indicator values
- Exposure/risk gauges

### Loop 2 — Portfolio State Stream (1s or bar close)

Risk engine snapshot updates:

- Position/equity/risk metric snapshots
- Sentinel panel gauges
- Command KPIs
- Equity curve append

### Loop 3 — Order/Fill Event Stream (event-driven)

Lifecycle events update:

- Order book
- Execution strip
- Positions tracker
- Alerts feed
- Session P&L state

Hard rule:

- Risk Sentinel + Kill Switch remain wired to Loops 2 and 3 even during heavy renders.

## 4) State Management Structure

### Global operator state

- Kill switch status
- Operating mode (LIVE/PAPER/BACKTEST)
- Strategy enable/disable roster
- Risk limit configuration
- Session start equity + watermark

### Live market state

- Symbol price map
- Position snapshots
- Order book by order ID
- Current risk metrics

### Historical audit state (append-only)

- Order history
- Alert history
- Parameter change history
- Risk breach history
- Fill tape

## 5) Operator Control Surface

### Soft controls

Immediate actions without confirmation:

- Pause/resume strategy
- Enable/disable symbol entries
- Panel collapse/expand
- Chart time range changes
- Order history filters

### Medium controls

Single-confirm actions:

- Manual order submit
- Order modify/cancel
- Stop-loss update
- Strategy parameter apply-to-live
- Export logs/fills/orders

### Hard controls

Press-hold or multi-confirm with reason:

- Kill switch activation
- Close all positions
- Live risk limit update
- Resume after halt (audited reason)
- PAPER → LIVE mode switch

## 6) Responsive Behavior

Primary target: **minimum 1920×1080** (ideal ultrawide/dual monitor).

At smaller widths:

- Alerts Feed collapses into status badge
- Execution Strip becomes slide-up tray
- Risk Sentinel collapses to persistent mini-panel
- Nav rail becomes icons-only

Constraint:

- Mobile live-trading operation is unsupported and should be blocked at auth layer.
