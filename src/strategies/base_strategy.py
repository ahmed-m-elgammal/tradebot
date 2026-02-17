"""
Base Strategy Class

Abstract base class for all trading strategies with signal generation and risk checks.
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.
    
    All strategy classes should inherit from this and implement:
    - generate_signals(): Convert indicators to trading signals
    - get_signal_description(): Return human-readable signal reason
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize strategy.
        
        Args:
            config: Strategy configuration dictionary
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals from market data.
        
        Args:
            df: DataFrame with OHLCV data and computed features
            
        Returns:
            DataFrame with 'signal' column added:
            - 1: Buy/Long
            - 0: No position/Flat
            - -1: Sell/Short
        """
        pass
    
    def get_signal_description(self, row: pd.Series) -> str:
        """
        Get human-readable description of why signal was generated.
        
        Args:
            row: DataFrame row with signal and indicators
            
        Returns:
            string description of signal reason
        """
        if row['signal'] == 1:
            return "Buy signal generated"
        elif row['signal'] == -1:
            return "Sell signal generated"
        else:
            return "No signal"
    
    def validate_signals(self, df: pd.DataFrame) -> None:
        """
        Validate that signals are correctly formed.
        
        Args:
            df: DataFrame with signals
            
        Raises:
            ValueError: If signals are invalid
        """
        if 'signal' not in df.columns:
            raise ValueError("DataFrame missing 'signal' column")
            
        # Signals must be -1, 0, or 1
        valid_signals = df['signal'].isin([-1, 0, 1])
        if not valid_signals.all():
            invalid_count = (~valid_signals).sum()
            raise ValueError(f"Found {invalid_count} invalid signal values (must be -1, 0, or 1)")
            
        # Check for NaN signals
        nan_count = df['signal'].isna().sum()
        if nan_count > 0:
            logger.warning(f"Found {nan_count} NaN signal values")
    
    def get_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Get statistics about generated signals.
        
        Args:
            df: DataFrame with signals
            
        Returns:
            Dictionary with signal statistics
        """
        if 'signal' not in df.columns:
            return {}
            
        total_bars = len(df)
        buy_signals = (df['signal'] == 1).sum()
        sell_signals = (df['signal'] == -1).sum()
        flat_signals = (df['signal'] == 0).sum()
        
        # Count signal changes (potential trades)
        signal_changes = (df['signal'].diff() != 0).sum()
        
        return {
            'total_bars': total_bars,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'flat_signals': flat_signals,
            'buy_pct': buy_signals / total_bars if total_bars > 0 else 0,
            'sell_pct': sell_signals / total_bars if total_bars > 0 else 0,
            'signal_changes': signal_changes,
            'avg_bars_per_trade': total_bars / signal_changes if signal_changes > 0 else float('inf')
        }
    
    def log_strategy_stats(self, df: pd.DataFrame) -> None:
        """
        Log statistics about strategy signals.
        
        Args:
            df: DataFrame with signals
        """
        stats = self.get_statistics(df)
        
        logger.info(f"Strategy: {self.name}")
        logger.info(f"  Total bars: {stats.get('total_bars', 0)}")
        logger.info(f"  Buy signals: {stats.get('buy_signals', 0)} ({stats.get('buy_pct', 0):.1%})")
        logger.info(f"  Sell signals: {stats.get('sell_signals', 0)} ({stats.get('sell_pct', 0):.1%})")
        logger.info(f"  Signal changes: {stats.get('signal_changes', 0)}")
        logger.info(f"  Avg bars per trade: {stats.get('avg_bars_per_trade', 0):.1f}")
