"""Phase 2 paper-trading layer tests."""

from src.execution import (
    OrderManager, PaperOrder, OrderState, RejectReason,
    SimulatedExchange, PositionTracker, ReconciliationEngine,
)
from src.risk.limits import RiskLimits, Position


def test_order_lifecycle_all_states_covered():
    manager = OrderManager()

    # created -> submitted -> partially_filled -> filled
    o1 = PaperOrder(symbol='BTC/USD', side='buy', quantity=10)
    assert o1.status == OrderState.CREATED
    o1 = manager.submit_order(o1)
    assert o1.status == OrderState.SUBMITTED
    o1 = manager.apply_fill(o1.id, fill_qty=4, fill_price=100)
    assert o1.status == OrderState.PARTIALLY_FILLED
    o1 = manager.apply_fill(o1.id, fill_qty=6, fill_price=101)
    assert o1.status == OrderState.FILLED

    # created -> submitted -> canceled
    o2 = PaperOrder(symbol='ETH/USD', side='buy', quantity=1)
    o2 = manager.submit_order(o2)
    o2 = manager.cancel_order(o2.id)
    assert o2.status == OrderState.CANCELED

    # created -> rejected (invalid)
    o3 = PaperOrder(symbol='SOL/USD', side='buy', quantity=1, order_type='limit', limit_price=None)
    o3 = manager.submit_order(o3)
    assert o3.status == OrderState.REJECTED
    assert o3.reject_reason == RejectReason.INVALID_ORDER.value


def test_kill_switch_and_circuit_breaker_rejections():
    manager = OrderManager(max_daily_loss_abs=100)
    manager.set_kill_switch(True)
    o = manager.submit_order(PaperOrder(symbol='BTC/USD', side='buy', quantity=1))
    assert o.reject_reason == RejectReason.KILL_SWITCH.value

    manager.set_kill_switch(False)
    manager.update_daily_realized_pnl(-150)
    o2 = manager.submit_order(PaperOrder(symbol='BTC/USD', side='buy', quantity=1))
    assert o2.reject_reason == RejectReason.MAX_LOSS_CIRCUIT_BREAKER.value


def test_exposure_precheck_before_submission():
    risk = RiskLimits({'max_position_size': 0.05, 'max_symbol_exposure': 0.05})
    manager = OrderManager(risk_limits=risk)

    open_positions = [Position(symbol='BTC/USD', quantity=5, entry_price=100, current_price=100)]  # $500
    # new order attempts +$1000 with equity $10k, should fail (symbol cap $500)
    o = PaperOrder(symbol='BTC/USD', side='buy', quantity=10, limit_price=100, order_type='limit')
    out = manager.submit_order(o, current_equity=10_000, open_positions=open_positions)
    assert out.status == OrderState.REJECTED
    assert out.reject_reason == RejectReason.RISK_CHECK_FAILED.value


def test_simulated_exchange_depth_aware_partial_fill():
    ex = SimulatedExchange(seed=1)
    limit = PaperOrder(symbol='BTC/USD', side='buy', quantity=10, order_type='limit', limit_price=100)

    result = ex.execute(limit, market_price=99, book_depth=1, volatility=0.01)
    assert 0 <= result['fill_ratio'] <= 1
    assert result['filled_qty'] <= limit.quantity

    metrics = ex.get_metrics()
    assert metrics['fill_events'] >= 1
    assert 'latency_histogram' in metrics


def test_position_tracker_realized_and_unrealized_pnl():
    tracker = PositionTracker()
    tracker.apply_fill('BTC/USD', 'buy', 2, 100)
    tracker.apply_fill('BTC/USD', 'sell', 1, 110)
    snap = tracker.snapshot({'BTC/USD': 105})

    assert snap['realized_pnl'] == 10
    assert abs(snap['unrealized_pnl'] - 5) < 1e-9


def test_reconciliation_detects_drift_missing_and_summary():
    rec = ReconciliationEngine(drift_tolerance=0.01)

    expected = {
        'positions': {'BTC/USD': {'quantity': 1.0, 'avg_entry_price': 100.0}},
        'update_count': 10,
    }
    actual = {
        'positions': {'BTC/USD': {'quantity': 0.8, 'avg_entry_price': 100.2}},
        'update_count': 8,
    }

    result = rec.reconcile(expected, actual)
    assert not result.ok
    assert result.missing_updates == 2

    summary = rec.daily_summary()
    assert summary['runs'] == 1
    assert summary['failed_runs'] == 1
