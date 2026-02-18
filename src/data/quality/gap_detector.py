"""
Enhanced Gap Detector with Logging and Config

Detects gaps in time series data with configurable thresholds.
"""

import pandas as pd
from datetime import timedelta
from typing import List, Dict, Optional

from src.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GapDetector:
    """
    Enhanced gap detector with logging and configuration.
    
    NEW FEATURES:
    - Configurable thresholds from config
    - Structured logging
    - Gap severity levels
    """
    
    def __init__(self, expected_interval_minutes: int = 1):
        """
        Initialize gap detector.
        
        Args:
            expected_interval_minutes: Expected time between bars
        """
        self.expected_interval = timedelta(minutes=expected_interval_minutes)
        
        # Load config
        try:
            config = get_config()
            self.max_gap_multiplier = config.data.quality.get('max_gap_multiplier', 3)
        except:
            self.max_gap_multiplier = 3
        
        self.max_allowed_gap = self.expected_interval * self.max_gap_multiplier
        
        logger.info("GapDetector initialized", extra={
            'expected_interval_min': expected_interval_minutes,
            'max_gap_min': self.max_allowed_gap.total_seconds() / 60
        })
    
    def detect_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect gaps in time series.
        
        Args:
            df: DataFrame with timestamp column
            
        Returns:
            List of gap dictionaries
        """
        if len(df) < 2:
            logger.debug("Insufficient data for gap detection")
            return []
        
        gaps = []
        
        # Calculate time differences
        df_sorted = df.sort_values('timestamp')
        time_diffs = df_sorted['timestamp'].diff()
        
        # Find gaps larger than expected + tolerance
        gap_mask = time_diffs > self.max_allowed_gap
        gap_indices = gap_mask[gap_mask].index
        
        for idx in gap_indices:
            gap_start = df_sorted.loc[idx - 1, 'timestamp']
            gap_end = df_sorted.loc[idx, 'timestamp']
            gap_duration = gap_end - gap_start
            
            gap_info = {
                'start': gap_start,
                'end': gap_end,
                'duration': gap_duration,
                'duration_minutes': gap_duration.total_seconds() / 60,
                'severity': self._calculate_severity(gap_duration)
            }
            
            gaps.append(gap_info)
        
        if gaps:
            logger.warning(f"Detected {len(gaps)} gaps", extra={
                'gap_count': len(gaps),
                'total_rows': len(df),
                'largest_gap_min': max(g['duration_minutes'] for g in gaps)
            })
        else:
            logger.debug("No gaps detected")
        
        return gaps
    
    def _calculate_severity(self, gap_duration: timedelta) -> str:
        """Calculate gap severity level."""
        minutes = gap_duration.total_seconds() / 60
        
        if minutes < 5:
            return 'LOW'
        elif minutes < 30:
            return 'MEDIUM'
        elif minutes < 60:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def fill_gaps(self, df: pd.DataFrame, method: str = 'ffill') -> pd.DataFrame:
        """
        Fill gaps using specified method.
        
        Args:
            df: DataFrame with gaps
            method: Fill method ('ffill', 'interpolate')
            
        Returns:
            DataFrame with filled gaps
        """
        if df.empty:
            return df
        
        original_len = len(df)
        
        # Create complete time range
        time_range = pd.date_range(
            start=df['timestamp'].min(),
            end=df['timestamp'].max(),
            freq=self.expected_interval
        )
        
        # Reindex to fill gaps
        df_filled = df.set_index('timestamp').reindex(time_range)
        
        if method == 'ffill':
            df_filled = df_filled.fillna(method='ffill')
        elif method == 'interpolate':
            df_filled = df_filled.interpolate(method='linear')
        
        df_filled = df_filled.reset_index().rename(columns={'index': 'timestamp'})
        
        filled_count = len(df_filled) - original_len
        
        if filled_count > 0:
            logger.info(f"Filled {filled_count} gaps using {method}", extra={
                'original_rows': original_len,
                'final_rows': len(df_filled),
                'filled_count': filled_count,
                'method': method
            })
        
        return df_filled
