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
from src.backtest.execution import ExecutionModel

logger = logging.getLogger(__name__)


class Backtester:
    """Vectorized backtesting engine."""

    def __init__(self,
                 initial_capital: float = 10000,
                 commission_pct: float = 0.001,
                 slippage_pct: float = 0.002,
                 spread_pct: float = 0.0005,
                 impact_pct: float = 0.0005,
                 default_risk_per_trade: float = 0.01,
                 execution_model: Optional[ExecutionModel] = None):
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.spread_pct = spread_pct
        self.impact_pct = impact_pct
        self.default_risk_per_trade = default_risk_per_trade

        self.total_cost_pct = commission_pct + slippage_pct
        self.execution_model = execution_model or ExecutionModel()

    def _resolve_volatility(self, data: pd.DataFrame) -> pd.Series:
        if 'atr' in data.columns and 'close' in data.columns:
            vol = (data['atr'] / data['close']).replace([np.inf, -np.inf], np.nan)
            return vol.fillna(0.0)
        return data['close'].pct_change().rolling(20).std().fillna(0.0)

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
        fallback_vol = self._resolve_volatility(data)

        for idx, row in data.iterrows():
            drawdown = 0.0 if equity_peak <= 0 else (equity_peak - equity) / equity_peak

            params = dict(sizing_params)
            if params.get('method') == 'volatility_based' and 'volatility' not in params:
                params['volatility'] = float(fallback_vol.loc[idx])

            position_size = position_sizer.calculate_position(
                signal=int(row['signal']),
                equity=equity,
                current_drawdown=drawdown,
                **params
            )
            position_fraction = np.sign(row['signal']) * (position_size / equity if equity > 0 else 0.0)
            positions.append(position_fraction)

            bar_ret = returns.loc[idx]
            equity = equity * (1 + (position_fraction * bar_ret))
            equity_peak = max(equity_peak, equity)

        return pd.Series(positions, index=data.index, dtype=float)

    def _apply_execution_model(self, data: pd.DataFrame) -> pd.Series:
        """Convert target position to realized position with partial fills."""
        order_types = data['order_type'] if 'order_type' in data.columns else pd.Series('market', index=data.index)
        book_depth = data['book_depth'] if 'book_depth' in data.columns else pd.Series(1.0, index=data.index)
        volatility = self._resolve_volatility(data)

        realized = []
        current_pos = 0.0
        for idx in data.index:
            target_pos = float(data.loc[idx, 'position'])
            delta = target_pos - current_pos
            fill = self.execution_model.simulate_fill(
                order_size=abs(delta),
                order_type=str(order_types.loc[idx]),
                book_depth=float(book_depth.loc[idx]),
                volatility=float(volatility.loc[idx]),
            )
            current_pos = current_pos + np.sign(delta) * abs(delta) * fill.fill_ratio
            realized.append((current_pos, fill.fee_multiplier))

        realized_pos = pd.Series([r[0] for r in realized], index=data.index, dtype=float)
        data['fee_multiplier'] = pd.Series([r[1] for r in realized], index=data.index, dtype=float)
        return realized_pos

    def run(self, strategy, data: pd.DataFrame, position_sizer=None, sizing_params: Optional[Dict] = None) -> tuple:
        """Run backtest on strategy."""
        start_ts = time.perf_counter()
        logger.info(f"Running backtest on {len(data)} bars...")

        data = strategy.generate_signals(data)
        if 'signal' not in data.columns:
            raise ValueError("Strategy did not generate 'signal' column")

        data['market_return'] = data['close'].pct_change(1).fillna(0.0)
        data['position'] = self._build_positions(data, position_sizer=position_sizer, sizing_params=sizing_params)
        data['realized_position'] = self._apply_execution_model(data)

        data['position_lagged'] = data['realized_position'].shift(1).fillna(0.0)
        data['strategy_return'] = data['position_lagged'] * data['market_return']

        data['position_change'] = data['realized_position'].diff().abs().fillna(data['realized_position'].abs())
        impact_cost = self.impact_pct * (1 + data['market_return'].abs() * 10)
        data['costs'] = data['position_change'] * (self.total_cost_pct + self.spread_pct + impact_cost) * data['fee_multiplier']

        data['net_return'] = (data['strategy_return'] - data['costs']).fillna(0.0)
        data['equity'] = self.initial_capital * (1 + data['net_return']).cumprod()
        data['equity'] = data['equity'].fillna(self.initial_capital)

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
