"""
Trading Strategies Module

This module provides trading strategy implementations with built-in risk management.

Modules:
    - base_strategy: Abstract base class for all strategies
    - mean_reversion: Mean reversion strategy using Bollinger Bands + RSI
    - signal_generator: Convert indicators to trading signals
    - position_sizer: Position sizing methods (Kelly, fixed fractional)
"""

from src.strategies.base_strategy import BaseStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.position_sizer import PositionSizer

__all__ = [
    'BaseStrategy',
    'MeanReversionStrategy',
    'PositionSizer',
]
