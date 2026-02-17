"""
Enhanced Outlier Detector with Logging and Config

Detects price outliers using configurable thresholds.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import sys
sys.path.insert(0, 'c:\\Users\\A-Dev\\Desktop\\Trading Bot')

from src.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OutlierDetector:
    """
    Enhanced outlier detector with logging and configuration.
    
    NEW FEATURES:
    - Configurable thresholds from config
    - Rolling window Z-scores
    - Structured logging
    - Multiple handling strategies
    """
    
    def __init__(self, z_threshold: float = 5.0, window: int = 20):
        """
        Initialize outlier detector.
        
        Args:
            z_threshold: Z-score threshold for outliers
            window: Rolling window for statistics
        """
        # Load config
        try:
            config = get_config()
            self.z_threshold = config.data.quality.get('outlier_z_threshold', z_threshold)
            self.window = config.data.quality.get('outlier_window', window)
        except:
            self.z_threshold = z_threshold
            self.window = window
        
        logger.info("OutlierDetector initialized", extra={
            'z_threshold': self.z_threshold,
            'window': self.window
        })
    
    def detect_price_outliers(self, df: pd.DataFrame, column: str = 'close') -> pd.DataFrame:
        """
        Detect outliers in price column using rolling Z-scores.
        
        Args:
            df: DataFrame with price data
            column: Column to check for outliers
            
        Returns:
            DataFrame with is_outlier column added
        """
        if df.empty or len(df) <self.window:
            logger.warning("Insufficient data for outlier detection")
            df['is_outlier'] = False
            return df
        
        df = df.copy()
        
        # Calculate rolling mean and std
        rolling_mean = df[column].rolling(window=self.window, center=True).mean()
        rolling_std = df[column].rolling(window=self.window, center=True).std()
        
        # Calculate Z-scores
        df['z_score'] = np.abs((df[column] - rolling_mean) / rolling_std)
        
        # Mark outliers
        df['is_outlier'] = df['z_score'] > self.z_threshold
        
        outlier_count = df['is_outlier'].sum()
        
        if outlier_count > 0:
            logger.warning(f"Detected {outlier_count} outliers in {column}", extra={
                'outlier_count': outlier_count,
                'total_rows': len(df),
                'outlier_pct': outlier_count / len(df) * 100,
                'max_z_score': df['z_score'].max()
            })
        else:
            logger.debug(f"No outliers detected in {column}")
        
        return df
    
    def handle_outliers(self, df: pd.DataFrame, method: str = 'cap', column: str = 'close') -> pd.DataFrame:
        """
        Handle detected outliers.
        
        Args:
            df: DataFrame with is_outlier column
            method: Handling method ('cap', 'remove', 'interpolate')
            column: Column to handle
            
        Returns:
            DataFrame with outliers handled
        """
        if 'is_outlier' not in df.columns:
            df = self.detect_price_outliers(df, column)
        
        outlier_count = df['is_outlier'].sum()
        
        if outlier_count == 0:
            return df
        
        df = df.copy()
        
        if method == 'cap':
            # Cap at mean ± 3*std
            mean = df[column].mean()
            std = df[column].std()
            lower_bound = mean - 3 * std
            upper_bound = mean + 3 * std
            
            df.loc[df['is_outlier'], column] = df.loc[df['is_outlier'], column].clip(lower_bound, upper_bound)
            logger.info(f"Capped {outlier_count} outliers", extra={
                'method': 'cap',
                'column': column,
                'count': outlier_count
            })
            
        elif method == 'remove':
            # Remove outlier rows
            df = df[~df['is_outlier']]
            logger.info(f"Removed {outlier_count} outliers", extra={
                'method': 'remove',
                'column': column,
                'count': outlier_count
            })
            
        elif method == 'interpolate':
            # Interpolate outlier values
            df.loc[df['is_outlier'], column] = np.nan
            df[column] = df[column].interpolate(method='linear')
            logger.info(f"Interpolated {outlier_count} outliers", extra={
                'method': 'interpolate',
                'column': column,
                'count': outlier_count
            })
        
        return df
