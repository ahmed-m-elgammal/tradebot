# Phase 1 Optimization Plan (Post-Review)

This plan converts the findings in `Phase1 review.md` into an execution-ready roadmap focused on correctness first, then robustness, then production-readiness.

## 1) Must Fix Immediately (Correctness)

### 1.1 Remove backtest lookahead bias
- **File**: `src/backtest/engine.py`
- **Issue**: `market_return` is shifted with `shift(-1)` and multiplied by current-bar position.
- **Risk**: Inflated performance metrics and invalid strategy evaluation.
- **Optimize to**:
  - Use same-bar returns: `close.pct_change(1)`
  - Apply prior-bar position: `position.shift(1) * market_return`
  - Fill initial NaNs safely (`0.0`) before equity compounding.
- **Done when**:
  - No forward-looking columns are used in PnL path.
  - Regression test confirms corrected returns logic.

### 1.2 Fix signal state transitions in mean reversion strategy
- **File**: `src/strategies/mean_reversion.py`
- **Issue**: Signal forward-fill is applied before exits, so exits can be neutralized by state propagation.
- **Risk**: Positions may persist incorrectly.
- **Optimize to**:
  - Compute entry events (`+1`, `-1`) and exit events independently.
  - Build a deterministic state machine:
    1. previous state
    2. apply exit
    3. apply entry
  - Avoid double `ffill` ambiguity by deriving explicit `position` state.
- **Done when**:
  - Unit test verifies position exits on exit condition bars.
  - No contradictory signal/position states.

### 1.3 Decide shorting scope for Phase 1
- **File**: `src/strategies/mean_reversion.py`
- **Issue**: Short logic exists but isn’t fully modeled as a first-class lifecycle (entry/hold/exit/risk).
- **Optimize to**:
  - **Option A (recommended for Phase 1)**: long-only + flat exits.
  - **Option B**: implement full short lifecycle + borrow/fee assumptions.
- **Done when**:
  - Signal semantics are consistent with backtester assumptions.

## 2) High-Value Risk Controls to Add

### 2.1 Strategy-level stop protections
- Add hard stop loss and optional time stop:
  - `max_loss_per_trade` (e.g., 3–5%)
  - `max_bars_in_trade` (timeout exit)
- Add volatility kill-switch:
  - Flat all positions when ATR/volatility regime exceeds threshold.

### 2.2 Drawdown-aware exposure scaling
- In `position_sizer`, reduce size as drawdown deepens.
- Example:
  - DD < 5%: 100% risk budget
  - DD 5–10%: 60% risk budget
  - DD > 10%: 30% risk budget or pause

### 2.3 Correlation and concentration guards
- Extend risk limits with:
  - max correlated exposure bucket
  - max symbol concentration
  - optional sector bucket limits

## 3) Backtesting Realism Improvements

### 3.1 Dynamic sizing integration
- Replace hardcoded `signal * 0.01` with ATR/volatility-based sizing.
- Keep risk-per-trade consistent with stop distance.

### 3.2 Fill and execution realism
- Add market impact / fill model:
  - spread-aware fills
  - slippage as function of volatility and turnover
  - optional partial fills for limit orders

### 3.3 Walk-forward validation module
- Add rolling train/test windows:
  - e.g., 252 bars train, 63 bars test
- Aggregate metrics across folds to reduce overfitting risk.

## 4) Data & Infrastructure Gaps to Close

### 4.1 Implement rate limiter utility
- **Gap**: Config mentions rate limiting but utility implementation is missing.
- Add `src/utils/rate_limiter.py` and integrate in data ingestors.

### 4.2 Strengthen ingest idempotency
- Deduplicate on timestamp/symbol/timeframe after pagination merges.
- Add explicit checks for missing or duplicate bars before feature computation.

### 4.3 Observability additions
- Add metric counters and periodic heartbeat logs:
  - ingest latency
  - signal counts
  - rejection reasons from risk engine
  - backtest runtime and memory footprint

## 5) Testing Upgrades (What to Add)

### 5.1 Deterministic correctness tests
- Backtester return alignment test (position shift correctness).
- Strategy transition test (entry/exit precedence).
- No-lookahead invariant tests for all feature columns.

### 5.2 Negative and edge-case tests
- Empty/single-row DataFrames.
- Invalid OHLCV ordering (high < low, negative volume, unsorted time).
- Risk rejection paths (max DD, max position, daily loss).

### 5.3 Performance budget tests
- Ensure backtest throughput target (e.g., 10k bars under target runtime).
- Fail build if runtime regresses beyond threshold.

## 6) Suggested Execution Order

1. Correctness fixes (lookahead + signal transitions + short scope decision)
2. Add tests that lock those fixes
3. Integrate dynamic sizing + stop protections
4. Add rate limiter and ingest idempotency checks
5. Add walk-forward validation
6. Add paper-trading execution components and monitoring

## 7) Success Criteria for “Phase 1 Optimized”

- Backtest is free from lookahead and passes alignment tests.
- Strategy entries/exits are deterministic and reproducible.
- Position sizing is risk-based, not hardcoded.
- Risk engine includes drawdown-aware throttling.
- Test suite includes negative/edge/performance checks.
- Walk-forward metrics are stable (not only single-split results).
- Paper trading stack has order lifecycle + reconciliation.
