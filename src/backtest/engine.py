"""
Backtesting Engine

Vectorized backtesting with realistic costs and performance metrics.
"""

import time
import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

from src.backtest.performance import PerformanceMetrics

logger = logging.getLogger(__name__)


class Backtester:
    """Vectorized backtesting engine."""

    def __init__(self,
                 initial_capital: float = 10000,
                 commission_pct: float = 0.001,
                 slippage_pct: float = 0.002,
                 spread_pct: float = 0.0005,
                 impact_pct: float = 0.0005,
                 default_risk_per_trade: float = 0.01):
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.spread_pct = spread_pct
        self.impact_pct = impact_pct
        self.default_risk_per_trade = default_risk_per_trade

        self.total_cost_pct = commission_pct + slippage_pct

    def _build_positions(self,
                         data: pd.DataFrame,
                         position_sizer=None,
                         sizing_params: Optional[Dict] = None) -> pd.Series:
        """Build equity-relative position fractions with optional dynamic sizing."""
        if position_sizer is None:
            return data['signal'].astype(float) * self.default_risk_per_trade

        sizing_params = sizing_params or {}
        equity = self.initial_capital
        equity_peak = self.initial_capital
        positions = []

        returns = data['close'].pct_change(1).fillna(0.0)

        for idx, row in data.iterrows():
            drawdown = 0.0 if equity_peak <= 0 else (equity_peak - equity) / equity_peak
            position_size = position_sizer.calculate_position(
                signal=int(row['signal']),
                equity=equity,
                current_drawdown=drawdown,
                **sizing_params
            )
            position_fraction = np.sign(row['signal']) * (position_size / equity if equity > 0 else 0.0)
            positions.append(position_fraction)

            bar_ret = returns.loc[idx]
            equity = equity * (1 + (position_fraction * bar_ret))
            equity_peak = max(equity_peak, equity)

        return pd.Series(positions, index=data.index, dtype=float)

    def run(self, strategy, data: pd.DataFrame, position_sizer=None, sizing_params: Optional[Dict] = None) -> tuple:
        """Run backtest on strategy."""
        start_ts = time.perf_counter()
        logger.info(f"Running backtest on {len(data)} bars...")

        data = strategy.generate_signals(data)
        if 'signal' not in data.columns:
            raise ValueError("Strategy did not generate 'signal' column")

        # Correct return alignment: current bar return, previous bar position.
        data['market_return'] = data['close'].pct_change(1).fillna(0.0)

        # Dynamic or default position sizing
        data['position'] = self._build_positions(data, position_sizer=position_sizer, sizing_params=sizing_params)

        # Use prior bar position to avoid lookahead.
        data['position_lagged'] = data['position'].shift(1).fillna(0.0)
        data['strategy_return'] = data['position_lagged'] * data['market_return']

        # Execution realism
        data['position_change'] = data['position'].diff().abs().fillna(data['position'].abs())
        impact_cost = self.impact_pct * (1 + data['market_return'].abs() * 10)
        data['costs'] = data['position_change'] * (self.total_cost_pct + self.spread_pct + impact_cost)

        data['net_return'] = (data['strategy_return'] - data['costs']).fillna(0.0)
        data['equity'] = self.initial_capital * (1 + data['net_return']).cumprod()
        data['equity'] = data['equity'].fillna(self.initial_capital)

        # Observability metrics
        runtime_s = time.perf_counter() - start_ts
        turnover = float(data['position_change'].sum())

        metrics = PerformanceMetrics.calculate_all(data, self.initial_capital)
        metrics['runtime_seconds'] = runtime_s
        metrics['avg_position'] = float(data['position_lagged'].abs().mean())
        metrics['turnover'] = turnover

        logger.info("Backtest complete", extra={
            'total_return': metrics['total_return'],
            'sharpe_ratio': metrics['sharpe_ratio'],
            'max_drawdown': metrics['max_drawdown'],
            'total_trades': metrics['total_trades'],
            'runtime_seconds': runtime_s,
            'turnover': turnover,
        })

        return data, metrics

    def run_with_position_sizing(self,
                                 strategy,
                                 data: pd.DataFrame,
                                 position_sizer,
                                 sizing_params: Optional[Dict] = None) -> tuple:
        """Backward-compatible wrapper for explicit sizing invocation."""
        return self.run(strategy, data, position_sizer=position_sizer, sizing_params=sizing_params)
