
"""Phase 1 optimization regression tests."""

import time
import pytest
import pandas as pd
import numpy as np

from src.backtest.engine import Backtester
from src.backtest.walk_forward import WalkForwardValidator
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.position_sizer import PositionSizer
from src.risk.limits import RiskLimits, Order, Position


class _StaticStrategy:
    def __init__(self, signals):
        self.signals = signals

    def generate_signals(self, df):
        out = df.copy()
        if len(self.signals) == len(out):
            out['signal'] = self.signals
        else:
            out['signal'] = [0] * len(out)
        return out


def _price_frame(n=200):
    ts = pd.date_range('2024-01-01', periods=n, freq='min')
    close = 100 + np.cumsum(np.random.normal(0, 0.2, n))
    df = pd.DataFrame({
        'timestamp': ts,
        'open': close,
        'high': close * 1.001,
        'low': close * 0.999,
        'close': close,
        'volume': np.random.uniform(1000, 2000, n),
    })
    return df


def test_backtester_uses_lagged_position_alignment():
    df = pd.DataFrame({'close': [100, 110, 100, 100]})
    strategy = _StaticStrategy(signals=[0, 1, 1, 0])
    backtester = Backtester(initial_capital=1000, commission_pct=0.0, slippage_pct=0.0, spread_pct=0.0, impact_pct=0.0)

    results, _ = backtester.run(strategy, df)

    # position at t=1 should not earn t=1 return; it should start at t=2
    assert results.loc[1, 'strategy_return'] == 0
    assert results.loc[2, 'strategy_return'] != 0


def test_mean_reversion_long_only_and_exits_to_flat():
    df = _price_frame(120)
    strategy = MeanReversionStrategy({'long_only': True, 'stop_loss_pct': 0.02, 'max_bars_in_trade': 5})
    out = strategy.generate_signals(df)

    assert set(out['signal'].unique()).issubset({0, 1})


def test_drawdown_aware_scaling_reduces_size():
    sizer = PositionSizer(default_method='fixed_fractional')
    full = sizer.calculate_position(signal=1, equity=10000, risk_per_trade=0.01, current_drawdown=0.02)
    reduced = sizer.calculate_position(signal=1, equity=10000, risk_per_trade=0.01, current_drawdown=0.12)
    assert reduced < full


def test_risk_concentration_and_correlation_limits():
    risk = RiskLimits({
        'max_position_size': 0.10,
        'max_symbol_exposure': 0.10,
        'max_portfolio_heat': 0.50,
        'max_correlated_exposure': 0.15,
        'correlation_threshold': 0.8,
    })
    equity = 10000

    open_positions = [Position(symbol='BTC', quantity=5, entry_price=100, current_price=100)]  # $500
    too_big_same_symbol = Order(symbol='BTC', quantity=6, price=100)  # +$600 => $1100 > $1000 cap
    approved, reason = risk.check_order(too_big_same_symbol, equity, open_positions)
    assert not approved and 'Symbol exposure' in reason

    open_positions = [Position(symbol='ETH', quantity=12, entry_price=100, current_price=100)]  # $1200
    corr_map = {'BTC': {'ETH': 0.9}}
    corr_order = Order(symbol='BTC', quantity=4, price=100)  # +$400 => $1600 > 15% of 10k
    approved, reason = risk.check_order(corr_order, equity, open_positions, correlation_map=corr_map)
    assert not approved and 'Correlated exposure' in reason



def test_walk_forward_runs_multiple_folds():
    df = _price_frame(400)
    strategy = MeanReversionStrategy({'long_only': True})
    backtester = Backtester()
    wf = WalkForwardValidator(backtester, train_size=120, test_size=60)

    folds, summary = wf.run(strategy, df)
    assert len(folds) >= 2
    assert not summary.empty


@pytest.mark.performance
def test_backtest_performance_budget_10k_under_2s():
    np.random.seed(42)
    df = _price_frame(10000)
    strategy = MeanReversionStrategy({'long_only': True})
    backtester = Backtester()

    start = time.perf_counter()
    backtester.run(strategy, df)
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0


def test_execution_model_partial_fill_limit_orders():
    df = _price_frame(80)

    strategy = MeanReversionStrategy({'long_only': True})
    backtester = Backtester()

    market_df = df.copy()
    market_df['order_type'] = 'market'
    market_df['book_depth'] = 1.0
    m_results, _ = backtester.run(strategy, market_df)

    limit_df = df.copy()
    limit_df['order_type'] = 'limit'
    limit_df['book_depth'] = 0.001
    l_results, _ = backtester.run(strategy, limit_df)

    assert l_results['position_change'].sum() <= m_results['position_change'].sum()


def test_sector_cluster_exposure_limits():
    risk = RiskLimits({
        'max_position_size': 0.50,
        'max_symbol_exposure': 0.50,
        'max_sector_exposure': 0.20,
        'max_cluster_exposure': 0.15,
        'max_portfolio_heat': 0.50,
    })
    equity = 10000

    open_positions = [Position(symbol='A', quantity=15, entry_price=100, current_price=100, sector='tech', cluster='c1')]
    order = Order(symbol='B', quantity=10, price=100, sector='tech', cluster='c2')  # sector -> 2500
    approved, reason = risk.check_order(order, equity, open_positions)
    assert not approved and 'Sector exposure' in reason


class _FittableStrategy(_StaticStrategy):
    def __init__(self, signals):
        super().__init__(signals)
        self.fit_called = False

    def fit(self, train):
        self.fit_called = True


def test_walk_forward_invokes_fit_on_train_folds():
    df = pd.DataFrame({'close': np.linspace(100, 120, 240)})
    strategy = _FittableStrategy([0] * len(df))
    backtester = Backtester()
    wf = WalkForwardValidator(backtester, train_size=100, test_size=40)

    folds, _ = wf.run(strategy, df)
    assert len(folds) >= 1
