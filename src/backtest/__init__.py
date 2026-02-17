"""
Backtesting Module

Tools for backtesting trading strategies with realistic costs and metrics.

Modules:
    - engine: Event-driven backtest execution
    - performance: Performance metrics calculation (Sharpe, Sortino, drawdown)
    - attribution: P&L breakdown and attribution analysis
"""

from src.backtest.engine import Backtester
from src.backtest.performance import PerformanceMetrics
from src.backtest.attribution import AttributionAnalyzer, Trade

__all__ = ['Backtester', 'PerformanceMetrics', 'AttributionAnalyzer', 'Trade']
