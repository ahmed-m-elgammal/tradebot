"""
Price Features

Fundamental price-based features including returns, volatility, and price ratios.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
import logging

from src.features.base_feature import BaseFeature

logger = logging.getLogger(__name__)


class PriceFeatures(BaseFeature):
    """
    Price-based feature engineering.
    
    Computes:
    - Returns (multiple horizons)
    - Volatility (rolling windows)
    - Price ratios (relative to moving averages)
    """
    
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all price features.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with additional price feature columns
        """
        logger.info("Computing price features...")
        
        df = df.copy()
        feature_cols = []
        
        # Returns
        df, return_cols = self.compute_returns(df, horizons=[5, 15, 60])
        feature_cols.extend(return_cols)
        
        # Volatility
        df, vol_cols = self.compute_volatility(df, windows=[20, 60])
        feature_cols.extend(vol_cols)
        
        # Price ratios
        df, ratio_cols = self.compute_price_ratios(df)
        feature_cols.extend(ratio_cols)
        
        # Log statistics
        self.log_feature_stats(df, feature_cols)
        
        # Validate no lookahead bias
        # Note: We don't validate target returns since they're meant to be forward-looking
        non_target_features = [c for c in feature_cols if not c.startswith('target_')]
        self.validate_no_lookahead(df, non_target_features)
        
        return df
    
    def compute_returns(self, df: pd.DataFrame, 
                       horizons: List[int] = [5, 15, 60]) -> tuple:
        """
        Compute forward and historical returns.
        
        CRITICAL: Forward returns (target_return_*) contain FUTURE information.
        These should ONLY be used as training targets, NEVER as input features.
        
        Args:
            df: DataFrame with OHLCV data
            horizons: List of periods for return calculation
            
        Returns:
            Tuple of (DataFrame, list of column names)
        """
        df = df.copy()
        cols = []
        
        for h in horizons:
            # TARGET RETURNS (FUTURE) - Use for training targets only
            # shift(-h) means this uses future data
            df[f'target_return_{h}min'] = df['close'].pct_change(h).shift(-h)
            cols.append(f'target_return_{h}min')
            
            # HISTORICAL RETURNS (SAFE) - Can be used as features
            # No shift means this only uses past data
            df[f'return_{h}min_lag'] = df['close'].pct_change(h)
            cols.append(f'return_{h}min_lag')
            
        logger.info(f"Computed returns for horizons: {horizons}")
        return df, cols
    
    def compute_volatility(self, df: pd.DataFrame, 
                          windows: List[int] = [20, 60]) -> tuple:
        """
        Compute rolling volatility.
        
        Args:
            df: DataFrame with OHLCV data
            windows: List of rolling window sizes
            
        Returns:
            Tuple of (DataFrame, list of column names)
        """
        df = df.copy()
        cols = []
        
        # Calculate returns for volatility
        returns = df['close'].pct_change()
        
        for w in windows:
            # Rolling standard deviation of returns
            df[f'volatility_{w}'] = returns.rolling(window=w).std()
            cols.append(f'volatility_{w}')
            
            # Parkinson volatility (uses high-low range)
            # More efficient estimator than close-to-close
            df[f'parkinson_vol_{w}'] = np.sqrt(
                (np.log(df['high'] / df['low']) ** 2).rolling(window=w).mean() / (4 * np.log(2))
            )
            cols.append(f'parkinson_vol_{w}')
            
        logger.info(f"Computed volatility for windows: {windows}")
        return df, cols
    
    def compute_price_ratios(self, df: pd.DataFrame) -> tuple:
        """
        Compute price relative to moving averages.
        
        These ratios indicate if price is above/below trend.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (DataFrame, list of column names)
        """
        df = df.copy()
        cols = []
        
        # Simple moving averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # Price ratios (>1 means price above average)
        df['price_to_sma20'] = df['close'] / df['sma_20']
        df['price_to_sma50'] = df['close'] / df['sma_50']
        df['price_to_sma200'] = df['close'] / df['sma_200']
        
        cols.extend(['price_to_sma20', 'price_to_sma50', 'price_to_sma200'])
        
        # Moving average crossovers
        df['sma20_to_sma50'] = df['sma_20'] / df['sma_50']
        df['sma50_to_sma200'] = df['sma_50'] / df['sma_200']
        
        cols.extend(['sma20_to_sma50', 'sma50_to_sma200'])
        
        # Distance from high/low
        df['pct_from_high'] = (df['close'] - df['high'].rolling(20).max()) / df['high'].rolling(20).max()
        df['pct_from_low'] = (df['close'] - df['low'].rolling(20).min()) / df['low'].rolling(20).min()
        
        cols.extend(['pct_from_high', 'pct_from_low'])
        
        logger.info(f"Computed {len(cols)} price ratio features")
        return df, cols
    
    def compute_intrabar_features(self, df: pd.DataFrame) -> tuple:
        """
        Compute features from within-bar information (OHLC).
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (DataFrame, list of column names)
        """
        df = df.copy()
        cols = []
        
        # High-Low range
        df['hl_range'] = (df['high'] - df['low']) / df['close']
        cols.append('hl_range')
        
        # Open-Close range
        df['oc_range'] = (df['close'] - df['open']) / df['open']
        cols.append('oc_range')
        
        # Upper shadow (wick above body)
        df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
        cols.append('upper_shadow')
        
        # Lower shadow (wick below body)
        df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']
        cols.append('lower_shadow')
        
        # Body ratio (how much of the range is the body)
        df['body_ratio'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-10)
        cols.append('body_ratio')
        
        logger.info(f"Computed {len(cols)} intrabar features")
        return df, cols
