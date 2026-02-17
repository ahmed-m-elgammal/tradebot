"""
Backtesting Engine

Vectorized backtesting with realistic costs and performance metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

from src.backtest.performance import PerformanceMetrics

logger = logging.getLogger(__name__)


class Backtester:
    """
    Vectorized backtesting engine.
    
    This implementation uses vectorized operations for speed.
    Applies realistic transaction costs (commission + slippage).
    """
    
    def __init__(self, 
                 initial_capital: float = 10000,
                 commission_pct: float = 0.001,
                 slippage_pct: float = 0.002):
        """
        Initialize backtester.
        
        Args:
            initial_capital: Starting equity
            commission_pct: Commission as % of trade value (e.g., 0.001 = 0.1%)
            slippage_pct: Slippage as % of trade value (e.g., 0.002 = 0.2%)
        """
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.total_cost_pct = commission_pct + slippage_pct
        
        logger.info(f"Backtester initialized:")
        logger.info(f"  Initial capital: ${initial_capital:.2f}")
        logger.info(f"  Commission: {commission_pct:.3%}")
        logger.info(f"  Slippage: {slippage_pct:.3%}")
        logger.info(f"  Total cost: {self.total_cost_pct:.3%}")
    
    def run(self, strategy, data: pd.DataFrame) -> tuple:
        """
        Run backtest on strategy.
        
        Args:
            strategy: Strategy instance with generate_signals() method
            data: DataFrame with OHLCV data
            
        Returns:
            Tuple of (results DataFrame, metrics dictionary)
        """
        logger.info(f"Running backtest on {len(data)} bars...")
        
        # Generate signals
        data = strategy.generate_signals(data)
        
        if 'signal' not in data.columns:
            raise ValueError("Strategy did not generate 'signal' column")
        
        # Calculate market returns (1-period forward)
        data['market_return'] = data['close'].pct_change(1).shift(-1)
        
        # Position sizing (simplified: fixed 1% per trade)
        # In production, would use PositionSizer here
        data['position'] = data['signal'] * 0.01  # 1% of equity per signal
        
        # Strategy returns (position * market return)
        data['strategy_return'] = data['position'] * data['market_return']
        
        # Transaction costs
        # Applied on position changes (trades)
        data['position_change'] = data['position'].diff().abs()
        data['costs'] = data['position_change'] * self.total_cost_pct
        
        # Net returns after costs
        data['net_return'] = data['strategy_return'] - data['costs']
        
        # Equity curve
        data['equity'] = self.initial_capital * (1 + data['net_return']).cumprod()
        
        # Fill NaN in first row
        data['equity'] = data['equity'].fillna(self.initial_capital)
        
        # Calculate performance metrics
        metrics = PerformanceMetrics.calculate_all(data, self.initial_capital)
        
        # Log summary
        logger.info(f"Backtest complete:")
        logger.info(f"  Total return: {metrics['total_return']:.2%}")
        logger.info(f"  Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
        logger.info(f"  Max drawdown: {metrics['max_drawdown']:.2%}")
        logger.info(f"  Total trades: {metrics['total_trades']}")
        logger.info(f"  Win rate: {metrics['win_rate']:.1%}")
        
        return data, metrics
    
    def run_with_position_sizing(self, 
                                 strategy,
                                 data: pd.DataFrame,
                                 position_sizer,
                                 sizing_params: Optional[Dict] = None) -> tuple:
        """
        Run backtest with proper position sizing.
        
        Args:
            strategy: Strategy instance
            data: OHLCV data
            position_sizer: PositionSizer instance
            sizing_params: Parameters for position sizing
            
        Returns:
            Tuple of (results DataFrame, metrics dictionary)
        """
        sizing_params = sizing_params or {}
        
        # Generate signals
        data = strategy.generate_signals(data)
        
        # Calculate position sizes
        equity = self.initial_capital
        positions = []
        
        for idx, row in data.iterrows():
            # Use position sizer
            position_size = position_sizer.calculate_position(
                signal=row['signal'],
                equity=equity,
                **sizing_params
            )
            
            # Convert to fraction of equity
            position_fraction = position_size / equity if equity > 0 else 0
            positions.append(position_fraction)
            
            # Update equity for next iteration (simplified)
            if idx > 0:
                ret = data.loc[idx, 'market_return']
                if not pd.isna(ret):
                    equity = equity * (1 + position_fraction * ret)
        
        data['position'] = positions
        
        # Continue with standard backtest logic
        data['market_return'] = data['close'].pct_change(1).shift(-1)
        data['strategy_return'] = data['position'] * data['market_return']
        data['position_change'] = data['position'].diff().abs()
        data['costs'] = data['position_change'] * self.total_cost_pct
        data['net_return'] = data['strategy_return'] - data['costs']
        data['equity'] = self.initial_capital * (1 + data['net_return']).cumprod()
        data['equity'] = data['equity'].fillna(self.initial_capital)
        
        metrics = PerformanceMetrics.calculate_all(data, self.initial_capital)
        
        return data, metrics
