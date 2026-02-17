"""
Performance Metrics

Calculate trading strategy performance metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """
    Calculate various performance metrics for trading strategies.
    
    Metrics:
    - Sharpe Ratio: Risk-adjusted returns
    - Sortino Ratio: Downside risk-adjusted returns
    - Maximum Drawdown: Largest peak-to-trough decline
    - Win Rate: Percentage of winning trades
    - Profit Factor: Gross profit / gross loss
    - Calmar Ratio: Return / max drawdown
    """
    
    @staticmethod
    def calculate_all(data: pd.DataFrame, initial_capital: float) -> Dict:
        """
        Calculate all performance metrics.
        
        Args:
            data: DataFrame with backtest results (must have 'net_return' and 'equity')
            initial_capital: Starting capital
            
        Returns:
            Dictionary with all metrics
        """
        returns = data['net_return'].dropna()
        equity = data['equity'].dropna()
        
        # Annualization factor (assuming minute bars, 252 days, 390 min/day)
        # Adjust based on your data frequency
        total_periods = len(returns)
        if total_periods == 0:
            return PerformanceMetrics._empty_metrics()
        
        # Determine frequency from timestamps if available
        if 'timestamp' in data.columns:
            time_diff = data['timestamp'].diff().median()
            if pd.notna(time_diff):
                minutes_per_bar = time_diff.total_seconds() / 60
                bars_per_day = (390 / minutes_per_bar) if minutes_per_bar > 0 else 390
            else:
                bars_per_day = 390  # Default to minute bars
        else:
            bars_per_day = 390
        
        annual_periods = 252 * bars_per_day
        
        metrics = {
            'sharpe_ratio': PerformanceMetrics.sharpe_ratio(returns, annual_periods),
            'sortino_ratio': PerformanceMetrics.sortino_ratio(returns, annual_periods),
            'max_drawdown': PerformanceMetrics.max_drawdown(equity),
            'total_return':  PerformanceMetrics.total_return(equity, initial_capital),
            'win_rate': PerformanceMetrics.win_rate(returns),
            'profit_factor': PerformanceMetrics.profit_factor(returns),
            'total_trades': PerformanceMetrics.total_trades(data),
            'avg_win': PerformanceMetrics.avg_win(returns),
            'avg_loss': PerformanceMetrics.avg_loss(returns),
            'calmar_ratio': 0.0  # Will calculate below
        }
        
        # Calmar = annual return / abs(max drawdown)
        annual_return = metrics['total_return'] * (annual_periods / total_periods)
        if metrics['max_drawdown'] < 0:
            metrics['calmar_ratio'] = annual_return / abs(metrics['max_drawdown'])
        
        return metrics
    
    @staticmethod
    def sharpe_ratio(returns: pd.Series, annual_periods: float) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted returns).
        
        Sharpe = (mean return / std return) * sqrt(periods per year)
        """
        if len(returns) < 2:
            return 0.0
            
        mean_return = returns.mean()
        std_return = returns.std()
        
        if std_return == 0:
            return 0.0
            
        sharpe = (mean_return / std_return) * np.sqrt(annual_periods)
        return sharpe
    
    @staticmethod
    def sortino_ratio(returns: pd.Series, annual_periods: float) -> float:
        """
        Calculate Sortino ratio (downside risk-adjusted returns).
        
        Only penalizes downside volatility.
        """
        if len(returns) < 2:
            return 0.0
            
        mean_return = returns.mean()
        downside_returns = returns[returns < 0]
        
        if len(downside_returns) == 0:
            return float('inf')
            
        downside_std = downside_returns.std()
        
        if downside_std == 0:
            return 0.0
            
        sortino = (mean_return / downside_std) * np.sqrt(annual_periods)
        return sortino
    
    @staticmethod
    def max_drawdown(equity: pd.Series) -> float:
        """
        Calculate maximum drawdown (peak to trough decline).
        
        Returns negative number (e.g., -0.15 for 15% drawdown).
        """
        if len(equity) < 2:
            return 0.0
            
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max
        max_dd = drawdown.min()
        
        return max_dd
    
    @staticmethod
    def total_return(equity: pd.Series, initial_capital: float) -> float:
        """Calculate total return."""
        if len(equity) == 0:
            return 0.0
            
        final_equity = equity.iloc[-1]
        return (final_equity / initial_capital) - 1
    
    @staticmethod
    def win_rate(returns: pd.Series) -> float:
        """Calculate win rate (% of profitable trades)."""
        trades = returns[returns != 0]
        
        if len(trades) == 0:
            return 0.0
            
        winning_trades = (trades > 0).sum()
        return winning_trades / len(trades)
    
    @staticmethod
    def profit_factor(returns: pd.Series) -> float:
        """
        Calculate profit factor (gross profit / gross loss).
        
        > 1 means profitable, < 1 means losing.
        """
        profits = returns[returns > 0].sum()
        losses = abs(returns[returns < 0].sum())
        
        if losses == 0:
            return float('inf') if profits > 0 else 0.0
            
        return profits / losses
    
    @staticmethod
    def total_trades(data: pd.DataFrame) -> int:
        """Count total number of trades (signal changes)."""
        if 'signal' not in data.columns:
            return 0
            
        # Count signal changes
        signal_changes = (data['signal'].diff() != 0).sum()
        return int(signal_changes)
    
    @staticmethod
    def avg_win(returns: pd.Series) -> float:
        """Average winning trade return."""
        wins = returns[returns > 0]
        return wins.mean() if len(wins) > 0 else 0.0
    
    @staticmethod
    def avg_loss(returns: pd.Series) -> float:
        """Average losing trade return (as positive number)."""
        losses = returns[returns < 0]
        return abs(losses.mean()) if len(losses) > 0 else 0.0
    
    @staticmethod
    def _empty_metrics() -> Dict:
        """Return empty metrics dictionary."""
        return {
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'total_return': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'total_trades': 0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'calmar_ratio': 0.0
        }
