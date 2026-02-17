"""
Base Feature Class

Abstract base class for all feature generators with timestamp validation
to prevent lookahead bias.
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class BaseFeature(ABC):
    """
    Base class for all feature generators with lookahead prevention.
    
    All feature classes should inherit from this and implement the compute() method.
    The base class provides utilities for validating that features don't contain
    future information (lookahead bias).
    """
    
    def __init__(self, validate_lookahead: bool = True):
        """
        Initialize base feature.
        
        Args:
            validate_lookahead: If True, run lookahead validation after compute
        """
        self.validate_lookahead = validate_lookahead
        
    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute features ensuring no future data leakage.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with additional feature columns
        """
        pass
    
    def validate_no_lookahead(self, df: pd.DataFrame, feature_cols: List[str], 
                             threshold: float = 0.8) -> None:
        """
        Verify features at timestamp T only use data from T and earlier.
        
        This checks that feature values don't correlate too strongly with
        future returns, which would indicate lookahead bias.
        
        Args:
            df: DataFrame with features
            feature_cols: List of feature column names to check
            threshold: Correlation threshold above which to raise error
            
        Raises:
            ValueError: If potential lookahead bias detected
        """
        if not self.validate_lookahead:
            return
            
        if 'close' not in df.columns:
            logger.warning("Cannot validate lookahead: 'close' column missing")
            return
            
        # Compute 1-period forward return
        future_return = df['close'].pct_change(1).shift(-1)
        
        issues = []
        for col in feature_cols:
            if col not in df.columns:
                continue
                
            # Skip if column has too many NaNs
            if df[col].isna().sum() / len(df) > 0.5:
                logger.warning(f"Skipping lookahead check for {col}: >50% NaN values")
                continue
                
            # Calculate correlation with future returns
            valid_mask = ~(df[col].isna() | future_return.isna())
            if valid_mask.sum() < 10:
                logger.warning(f"Skipping lookahead check for {col}: insufficient data")
                continue
                
            correlation = df.loc[valid_mask, col].corr(future_return[valid_mask])
            
            if abs(correlation) > threshold:
                issues.append(f"{col}: correlation={correlation:.3f}")
                
        if issues:
            error_msg = f"Potential lookahead bias detected:\n" + "\n".join(issues)
            logger.error(error_msg)
            raise ValueError(error_msg)
        else:
            logger.info(f"Lookahead validation passed for {len(feature_cols)} features")
    
    def check_feature_health(self, df: pd.DataFrame, feature_cols: List[str]) -> dict:
        """
        Check health metrics for computed features.
        
        Args:
            df: DataFrame with features
            feature_cols: List of feature column names to check
            
        Returns:
            Dictionary with health metrics per feature
        """
        health = {}
        
        for col in feature_cols:
            if col not in df.columns:
                continue
                
            health[col] = {
                'nan_count': df[col].isna().sum(),
                'nan_pct': df[col].isna().sum() / len(df),
                'inf_count': np.isinf(df[col]).sum(),
                'mean': df[col].mean() if df[col].dtype in [np.float64, np.int64] else None,
                'std': df[col].std() if df[col].dtype in [np.float64, np.int64] else None,
                'min': df[col].min() if df[col].dtype in [np.float64, np.int64] else None,
                'max': df[col].max() if df[col].dtype in [np.float64, np.int64] else None,
            }
            
        return health
    
    def log_feature_stats(self, df: pd.DataFrame, feature_cols: List[str]) -> None:
        """
        Log statistics about computed features.
        
        Args:
            df: DataFrame with features
            feature_cols: List of feature column names
        """
        health = self.check_feature_health(df, feature_cols)
        
        logger.info(f"Computed {len(feature_cols)} features:")
        for col, stats in health.items():
            if stats['nan_pct'] > 0.1:
                logger.warning(f"  {col}: {stats['nan_pct']:.1%} NaN values")
            else:
                logger.info(f"  {col}: {stats['nan_pct']:.1%} NaN, "
                          f"range=[{stats['min']:.4f}, {stats['max']:.4f}]")
