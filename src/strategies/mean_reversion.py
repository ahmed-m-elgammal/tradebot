"""
Mean Reversion Trading Strategy

Simple mean reversion strategy using Bollinger Bands and RSI.

Entry Logic:
- BUY when price < lower Bollinger Band AND RSI < oversold threshold
- SELL when price > upper Bollinger Band AND RSI > overbought threshold

Exit Logic:
- Exit long when price > middle Bollinger Band OR RSI > overbought
- Exit short when price < middle Bollinger Band OR RSI < oversold
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

from src.strategies.base_strategy import BaseStrategy
from src.features.technical_indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion strategy using Bollinger Bands and RSI.
    
    This strategy assumes that extreme price movements are temporary
    and price will revert to the mean.
    
    Configuration:
        - bollinger_window: Moving average window for Bollinger Bands (default: 20)
        - bollinger_std: Standard deviations for bands (default: 2.0)
        - rsi_window: RSI calculation window (default: 14)
        - rsi_oversold: RSI oversold threshold (default: 30)
        - rsi_overbought: RSI overbought threshold (default: 70)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize mean reversion strategy.
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        
        # Bollinger Band parameters
        self.bb_window = self.config.get('bollinger_window', 20)
        self.bb_std = self.config.get('bollinger_std', 2.0)
        
        # RSI parameters
        self.rsi_window = self.config.get('rsi_window', 14)
        self.rsi_oversold = self.config.get('rsi_oversold', 30)
        self.rsi_overbought = self.config.get('rsi_overbought', 70)
        
        logger.info(f"Initialized {self.name} with:")
        logger.info(f"  Bollinger: window={self.bb_window}, std={self.bb_std}")
        logger.info(f"  RSI: window={self.rsi_window}, oversold={self.rsi_oversold}, overbought={self.rsi_overbought}")
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on Bollinger Bands and RSI.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with 'signal' column:
            - 1: Buy (oversold)
            - -1: Sell (overbought)  
            - 0: Hold/flat
        """
        df = df.copy()
        
        # Compute indicators if not already present
        indicators = TechnicalIndicators(validate_lookahead=False)
        
        if 'bb_upper' not in df.columns:
            df = indicators.add_bollinger_bands(df, window=self.bb_window, std=self.bb_std)
            
        if 'rsi' not in df.columns:
            df = indicators.add_rsi(df, window=self.rsi_window)
        
        # Initialize signal column
        df['signal'] = 0
        
        # Buy signals: Oversold conditions
        # Price below lower band AND RSI oversold
        buy_condition = (
            (df['close'] < df['bb_lower']) &
            (df['rsi'] < self.rsi_oversold)
        )
        
        # Sell signals: Overbought conditions
        # Price above upper band AND RSI overbought
        sell_condition = (
            (df['close'] > df['bb_upper']) &
            (df['rsi'] > self.rsi_overbought)
        )
        
        # Assign signals
        df.loc[buy_condition, 'signal'] = 1
        df.loc[sell_condition, 'signal'] = -1
        
        # Forward-fill signals to maintain position until opposite signal
        # This creates position-holding logic
        df['signal'] = df['signal'].replace(0, np.nan).ffill().fillna(0).astype(int)
        
        # Exit conditions: Return to mean
        # Exit long when price returns above middle band OR RSI normalizes
        exit_long = (
            (df['signal'].shift(1) == 1) &  # Currently long
            ((df['close'] > df['bb_middle']) | (df['rsi'] > self.rsi_overbought))
        )
        
        # Exit short when price returns below middle band OR RSI normalizes
        exit_short = (
            (df['signal'].shift(1) == -1) &  # Currently short
            ((df['close'] < df['bb_middle']) | (df['rsi'] < self.rsi_oversold))
        )
        
        # Set signal to 0 on exit conditions
        df.loc[exit_long | exit_short, 'signal'] = 0
        
        # Validate signals
        self.validate_signals(df)
        
        # Log statistics
        self.log_strategy_stats(df)
        
        return df
    
    def get_signal_description(self, row: pd.Series) -> str:
        """
        Get detailed description of signal.
        
        Args:
            row: DataFrame row with indicator values
            
        Returns:
            Human-readable signal description
        """
        if row['signal'] == 1:
            return (f"BUY: Price ({row['close']:.2f}) below lower BB ({row['bb_lower']:.2f}), "
                   f"RSI ({row['rsi']:.1f}) oversold (< {self.rsi_oversold})")
        elif row['signal'] == -1:
            return (f"SELL: Price ({row['close']:.2f}) above upper BB ({row['bb_upper']:.2f}), "
                   f"RSI ({row['rsi']:.1f}) overbought (> {self.rsi_overbought})")
        else:
            if 'bb_middle' in row and 'rsi' in row:
                return f"FLAT: Price near mean ({row['bb_middle']:.2f}), RSI neutral ({row['rsi']:.1f})"
            return "FLAT: No signal"
    
    def get_entry_price_targets(self, row: pd.Series) -> Dict:
        """
        Get suggested entry prices and targets.
        
        Args:
            row: DataFrame row with current market data
            
        Returns:
            Dictionary with entry, stop, and target prices
        """
        if row['signal'] == 1:  # Buy signal
            return {
                'entry': row['close'],
                'stop_loss': row['bb_lower'] * 0.98,  # 2% below lower band
                'take_profit': row['bb_middle'],       # Middle band (mean)
                'risk_reward': abs((row['bb_middle'] - row['close']) / 
                                 (row['close'] - row['bb_lower'] * 0.98))
            }
        elif row['signal'] == -1:  # Sell signal
            return {
                'entry': row['close'],
                'stop_loss': row['bb_upper'] * 1.02,  # 2% above upper band
                'take_profit': row['bb_middle'],       # Middle band (mean)
                'risk_reward': abs((row['close'] - row['bb_middle']) / 
                                 (row['bb_upper'] * 1.02 - row['close']))
            }
        else:
            return {}
