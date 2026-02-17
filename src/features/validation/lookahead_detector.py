"""
Lookahead Bias Detector

CRITICAL MODULE: Prevents using future information in features.

Lookahead bias is the #1 cause of backtest-to-live performance degradation.
This detector must be run on ALL features before backtesting.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class LookaheadDetector:
    """
    Detects if features contain future information (lookahead bias).
    
    Method: Check if feature values correlate strongly with future returns.
    A legitimate feature should not predict future returns too perfectly.
    
    Example:
        >>> detector = LookaheadDetector()
        >>> df['bad_feature'] = df['close'].shift(-5)  # Uses future data!
        >>> results = detector.detect_lookahead(df, ['bad_feature'])
        >>> # results['bad_feature']['status'] == 'FAIL'
    """
    
    def __init__(self, correlation_threshold: float = 0.7, 
                 forward_periods: int = 10):
        """
        Initialize lookahead detector.
        
        Args:
            correlation_threshold: Correlation above this raises warning
            forward_periods: How many periods ahead to check
        """
        self.correlation_threshold = correlation_threshold
        self.forward_periods = forward_periods
        
    def detect_lookahead(self, df: pd.DataFrame, 
                        feature_cols: List[str],
                        price_col: str = 'close') -> Dict:
        """
        Detect if features contain future information.
        
        This checks correlation between features and future returns at
        multiple horizons. High correlation suggests lookahead bias.
        
        Args:
            df: DataFrame with features and price data
            feature_cols: List of feature column names to check
            price_col: Price column to use for returns (default: 'close')
            
        Returns:
            Dictionary with results per feature:
            {
                'feature_name': {
                    'status': 'PASS' or 'FAIL' or 'WARNING',
                    'max_correlation': float,
                    'worst_period': int,
                    'message': str,
                    'all_correlations': dict
                }
            }
        """
        if price_col not in df.columns:
            raise ValueError(f"Price column '{price_col}' not found in DataFrame")
            
        results = {}
        
        for col in feature_cols:
            if col not in df.columns:
                results[col] = {
                    'status': 'SKIP',
                    'message': f'Feature column {col} not found'
                }
                continue
                
            # Check feature at multiple forward horizons
            correlations = {}
            max_corr = 0
            worst_period = 0
            
            for period in range(1, self.forward_periods + 1):
                # Calculate future return
                future_return = df[price_col].pct_change(period).shift(-period)
                
                # Skip if too many NaN values
                valid_mask = ~(df[col].isna() | future_return.isna())
                if valid_mask.sum() < 20:
                    continue
                    
                # Calculate correlation
                corr = df.loc[valid_mask, col].corr(future_return[valid_mask])
                correlations[period] = corr
                
                # Track maximum absolute correlation
                if abs(corr) > abs(max_corr):
                    max_corr = corr
                    worst_period = period
                    
            # Determine status
            abs_max_corr = abs(max_corr)
            
            if abs_max_corr > 0.9:
                status = 'FAIL'
                message = f'CRITICAL: Very high correlation ({max_corr:.3f}) with {worst_period}-period future return. Likely lookahead bias!'
            elif abs_max_corr > self.correlation_threshold:
                status = 'WARNING'
                message = f'High correlation ({max_corr:.3f}) with {worst_period}-period future return. Possible lookahead bias.'
            else:
                status = 'PASS'
                message = f'Max correlation ({max_corr:.3f}) within acceptable range.'
                
            results[col] = {
                'status': status,
                'max_correlation': max_corr,
                'worst_period': worst_period,
                'message': message,
                'all_correlations': correlations
            }
            
            # Log results
            if status == 'FAIL':
                logger.error(f"Lookahead check FAILED for {col}: {message}")
            elif status == 'WARNING':
                logger.warning(f"Lookahead check WARNING for {col}: {message}")
            else:
                logger.debug(f"Lookahead check PASSED for {col}")
                
        return results
    
    def verify_no_lookahead(self, df: pd.DataFrame, 
                           feature_cols: List[str],
                           raise_on_fail: bool = True) -> bool:
        """
        Verify that no lookahead bias exists in features.
        
        Args:
            df: DataFrame with features
            feature_cols: List of feature column names to check
            raise_on_fail: If True, raise exception on failure
            
        Returns:
            True if all features pass, False otherwise
            
        Raises:
            ValueError: If lookahead bias detected and raise_on_fail=True
        """
        results = self.detect_lookahead(df, feature_cols)
        
        failures = [col for col, res in results.items() if res['status'] == 'FAIL']
        warnings = [col for col, res in results.items() if res['status'] == 'WARNING']
        
        if failures:
            error_msg = f"Lookahead bias detected in features: {', '.join(failures)}\n"
            for col in failures:
                error_msg += f"  {col}: {results[col]['message']}\n"
                
            if raise_on_fail:
                raise ValueError(error_msg)
            else:
                logger.error(error_msg)
                return False
                
        if warnings:
            warning_msg = f"Possible lookahead bias in features: {', '.join(warnings)}"
            logger.warning(warning_msg)
            
        logger.info(f"Lookahead validation: {len(results) - len(failures) - len(warnings)} PASS, "
                   f"{len(warnings)} WARNING, {len(failures)} FAIL")
        
        return len(failures) == 0
    
    def analyze_feature_timing(self, df: pd.DataFrame, 
                               feature_col: str,
                               price_col: str = 'close',
                               max_lag: int = 20) -> Dict:
        """
        Analyze the timing relationship between a feature and price.
        
        This checks if the feature is most correlated with past, present,
        or future prices. A good feature should correlate most with past/present.
        
        Args:
            df: DataFrame with feature and price
            feature_col: Feature column to analyze
            price_col: Price column
            max_lag: Maximum lag to check (both directions)
            
        Returns:
            Dictionary with timing analysis
        """
        if feature_col not in df.columns or price_col not in df.columns:
            raise ValueError("Feature or price column not found")
            
        correlations = {}
        
        # Check correlations at different lags
        for lag in range(-max_lag, max_lag + 1):
            if lag < 0:
                # Negative lag: feature vs future price (BAD)
                shifted_price = df[price_col].shift(lag)
            else:
                # Positive lag: feature vs past price (GOOD)
                shifted_price = df[price_col].shift(lag)
                
            valid_mask = ~(df[feature_col].isna() | shifted_price.isna())
            if valid_mask.sum() < 20:
                continue
                
            corr = df.loc[valid_mask, feature_col].corr(shifted_price[valid_mask])
            correlations[lag] = corr
            
        # Find lag with maximum correlation
        max_lag_corr = max(correlations.items(), key=lambda x: abs(x[1]))
        
        # Determine if timing is suspicious
        if max_lag_corr[0] < 0:
            timing_status = 'SUSPICIOUS'
            timing_msg = f'Feature correlates most with future price (lag={max_lag_corr[0]})'
        else:
            timing_status = 'OK'
            timing_msg = f'Feature correlates most with past price (lag={max_lag_corr[0]})'
            
        return {
            'status': timing_status,
            'message': timing_msg,
            'max_correlation': max_lag_corr[1],
            'max_correlation_lag': max_lag_corr[0],
            'all_correlations': correlations
        }
    
    def generate_report(self, df: pd.DataFrame, 
                       feature_cols: List[str]) -> str:
        """
        Generate a comprehensive lookahead bias report.
        
        Args:
            df: DataFrame with features
            feature_cols: List of feature columns
            
        Returns:
            Formatted report string
        """
        results = self.detect_lookahead(df, feature_cols)
        
        report = "=" * 60 + "\n"
        report += "LOOKAHEAD BIAS DETECTION REPORT\n"
        report += "=" * 60 + "\n\n"
        
        # Summary
        pass_count = sum(1 for r in results.values() if r['status'] == 'PASS')
        warn_count = sum(1 for r in results.values() if r['status'] == 'WARNING')
        fail_count = sum(1 for r in results.values() if r['status'] == 'FAIL')
        
        report += f"Total Features: {len(results)}\n"
        report += f"  PASS: {pass_count}\n"
        report += f"  WARNING: {warn_count}\n"
        report += f"  FAIL: {fail_count}\n\n"
        
        # Details
        if fail_count > 0:
            report += "FAILURES:\n"
            report += "-" * 60 + "\n"
            for col, res in results.items():
                if res['status'] == 'FAIL':
                    report += f"  {col}:\n"
                    report += f"    {res['message']}\n"
                    report += f"    Max correlation: {res['max_correlation']:.3f} at period {res['worst_period']}\n"
            report += "\n"
            
        if warn_count > 0:
            report += "WARNINGS:\n"
            report += "-" * 60 + "\n"
            for col, res in results.items():
                if res['status'] == 'WARNING':
                    report += f"  {col}:\n"
                    report += f"    {res['message']}\n"
            report += "\n"
            
        report += "=" * 60 + "\n"
        
        return report
