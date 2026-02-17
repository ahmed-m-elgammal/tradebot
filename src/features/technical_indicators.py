"""
Technical Indicators

Common technical indicators used in trading strategies.
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging

from src.features.base_feature import BaseFeature

logger = logging.getLogger(__name__)


class TechnicalIndicators(BaseFeature):
    """
    Technical indicator feature engineering.
    
    Computes:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Bollinger Bands
    - Moving Averages (SMA, EMA)
    """
    
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all technical indicators.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with additional indicator columns
        """
        logger.info("Computing technical indicators...")
        
        df = df.copy()
        feature_cols = []
        
        # RSI
        df = self.add_rsi(df, window=14)
        feature_cols.append('rsi')
        
        # MACD
        df = self.add_macd(df)
        feature_cols.extend(['macd', 'macd_signal', 'macd_hist'])
        
        # Bollinger Bands
        df = self.add_bollinger_bands(df, window=20, std=2)
        feature_cols.extend(['bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position'])
        
        # Moving Averages
        df = self.add_moving_averages(df)
        feature_cols.extend(['sma_10', 'sma_20', 'sma_50', 'ema_12', 'ema_26'])
        
        # Log statistics
        self.log_feature_stats(df, feature_cols)
        
        # Validate no lookahead bias
        self.validate_no_lookahead(df, feature_cols)
        
        return df
    
    def add_rsi(self, df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
        """
        Add Relative Strength Index (RSI).
        
        RSI measures momentum and ranges from 0 to 100.
        - RSI > 70: Overbought
        - RSI < 30: Oversold
        
        Args:
            df: DataFrame with OHLCV data
            window: Lookback window for RSI calculation
            
        Returns:
            DataFrame with 'rsi' column
        """
        df = df.copy()
        
        # Calculate price changes
        delta = df['close'].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss using EMA
        avg_gain = gain.ewm(alpha=1/window, min_periods=window).mean()
        avg_loss = loss.ewm(alpha=1/window, min_periods=window).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / (avg_loss + 1e-10)  # Add small value to avoid division by zero
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Ensure RSI is within [0, 100]
        df['rsi'] = df['rsi'].clip(0, 100)
        
        logger.debug(f"Added RSI with window={window}")
        return df
    
    def add_macd(self, df: pd.DataFrame, 
                 fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """
        Add MACD (Moving Average Convergence Divergence).
        
        MACD shows trend direction and momentum.
        - MACD > Signal: Bullish
        - MACD < Signal: Bearish
        - MACD histogram crossing zero: Potential trend change
        
        Args:
            df: DataFrame with OHLCV data
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line EMA period
            
        Returns:
            DataFrame with 'macd', 'macd_signal', 'macd_hist' columns
        """
        df = df.copy()
        
        # Calculate EMAs
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        
        # MACD line
        df['macd'] = ema_fast - ema_slow
        
        # Signal line
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        
        # MACD histogram
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        logger.debug(f"Added MACD with fast={fast}, slow={slow}, signal={signal}")
        return df
    
    def add_bollinger_bands(self, df: pd.DataFrame, 
                           window: int = 20, std: float = 2.0) -> pd.DataFrame:
        """
        Add Bollinger Bands.
        
        Bollinger Bands show price volatility and potential reversal points.
        - Price touching upper band: Overbought
        - Price touching lower band: Oversold
        - Narrow bands: Low volatility (potential breakout)
        - Wide bands: High volatility
        
        Args:
            df: DataFrame with OHLCV data
            window: Moving average window
            std: Number of standard deviations for bands
            
        Returns:
            DataFrame with 'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position' columns
        """
        df = df.copy()
        
        # Middle band (SMA)
        df['bb_middle'] = df['close'].rolling(window=window).mean()
        
        # Standard deviation
        rolling_std = df['close'].rolling(window=window).std()
        
        # Upper and lower bands
        df['bb_upper'] = df['bb_middle'] + (std * rolling_std)
        df['bb_lower'] = df['bb_middle'] - (std * rolling_std)
        
        # Band width (normalized)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Price position within bands (0 = lower, 1 = upper)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-10)
        df['bb_position'] = df['bb_position'].clip(0, 1)
        
        logger.debug(f"Added Bollinger Bands with window={window}, std={std}")
        return df
    
    def add_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add various moving averages.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with SMA and EMA columns
        """
        df = df.copy()
        
        # Simple Moving Averages
        df['sma_10'] = df['close'].rolling(window=10).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # Exponential Moving Averages
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        logger.debug("Added moving averages (SMA: 10,20,50; EMA: 12,26)")
        return df
    
    def add_stochastic(self, df: pd.DataFrame, 
                      k_window: int = 14, d_window: int = 3) -> pd.DataFrame:
        """
        Add Stochastic Oscillator.
        
        Stochastic compares closing price to price range over period.
        - %K > 80: Overbought
        - %K < 20: Oversold
        
        Args:
            df: DataFrame with OHLCV data
            k_window: Lookback window for %K
            d_window: Smoothing window for %D
            
        Returns:
            DataFrame with 'stoch_k' and 'stoch_d' columns
        """
        df = df.copy()
        
        # Calculate %K
        low_min = df['low'].rolling(window=k_window).min()
        high_max = df['high'].rolling(window=k_window).max()
        
        df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min + 1e-10)
        
        # Calculate %D (smoothed %K)
        df['stoch_d'] = df['stoch_k'].rolling(window=d_window).mean()
        
        logger.debug(f"Added Stochastic with k_window={k_window}, d_window={d_window}")
        return df
    
    def add_atr(self, df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
        """
        Add Average True Range (ATR).
        
        ATR measures volatility and is useful for position sizing.
        
        Args:
            df: DataFrame with OHLCV data
            window: Lookback window
            
        Returns:
            DataFrame with 'atr' column
        """
        df = df.copy()
        
        # True Range calculation
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Average True Range (EMA of TR)
        df['atr'] = true_range.ewm(alpha=1/window, min_periods=window).mean()
        
        logger.debug(f"Added ATR with window={window}")
        return df
