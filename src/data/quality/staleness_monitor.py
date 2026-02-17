"""
Enhanced Staleness Monitor with Logging and Alerting

Monitors data staleness with configurable thresholds.
"""

import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import sys
sys.path.insert(0, 'c:\\Users\\A-Dev\\Desktop\\Trading Bot')

from src.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StalenessMonitor:
    """
    Enhanced staleness monitor with logging and alerting.
    
    NEW FEATURES:
    - Configurable thresholds from config
    - Structured logging with alerts
    - Staleness history tracking
    - Multiple severity levels
    """
    
    def __init__(self, threshold_minutes: int = 15):
        """
        Initialize staleness monitor.
        
        Args:
            threshold_minutes: Alert threshold in minutes
        """
        # Load config
        try:
            config = get_config()
            self.threshold_minutes = config.data.quality.staleness_threshold_minutes
        except:
            self.threshold_minutes = threshold_minutes
        
        self.staleness_history = []
        
        logger.info("StalenessMonitor initialized", extra={
            'threshold_minutes': self.threshold_minutes
        })
    
    def check_staleness(self, df: pd.DataFrame) -> Dict:
        """
        Check data staleness and log alerts.
        
        Args:
            df: DataFrame with timestamp column
            
        Returns:
            Dictionary with staleness info
        """
        if df.empty:
            logger.warning("Empty DataFrame provided to staleness check")
            return {'is_stale': False, 'age_minutes': 0}
        
        # Get latest timestamp
        last_timestamp = df['timestamp'].max()
        
        # Handle timezone
        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
        else:
            last_timestamp = last_timestamp.tz_convert('UTC')
        
        now = datetime.now(timezone.utc)
        age = now - last_timestamp
        age_minutes = age.total_seconds() / 60
        
        is_stale = age_minutes > self.threshold_minutes
        severity = self._calculate_severity(age_minutes)
        
        result = {
            'is_stale': is_stale,
            'age_minutes': age_minutes,
            'last_timestamp': last_timestamp.isoformat(),
            'checked_at': now.isoformat(),
            'severity': severity
        }
        
        # Log based on severity
        if severity == 'CRITICAL':
            logger.error(f"CRITICAL: Data extremely stale ({age_minutes:.1f} min old)", extra=result)
        elif severity == 'HIGH':
            logger.warning(f"WARNING: Data is stale ({age_minutes:.1f} min old)", extra=result)
        elif severity == 'MEDIUM':
            logger.info(f"Data approaching staleness ({age_minutes:.1f} min old)", extra=result)
        else:
            logger.debug(f"Data is fresh ({age_minutes:.1f} min old)")
        
        # Track history
        self.staleness_history.append(result)
        
        # Keep only last 100 checks
        if len(self.staleness_history) > 100:
            self.staleness_history = self.staleness_history[-100:]
        
        return result
    
    def _calculate_severity(self, age_minutes: float) -> str:
        """Calculate staleness severity."""
        if age_minutes < self.threshold_minutes:
            return 'OK'
        elif age_minutes < self.threshold_minutes * 2:
            return 'MEDIUM'
        elif age_minutes < self.threshold_minutes * 5:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def get_staleness_stats(self) -> Dict:
        """Get staleness history statistics."""
        if not self.staleness_history:
            return {}
        
        stale_count = sum(1 for h in self.staleness_history if h['is_stale'])
        
        return {
            'total_checks': len(self.staleness_history),
            'stale_count': stale_count,
            'stale_rate': stale_count / len(self.staleness_history),
            'recent_check': self.staleness_history[-1] if self.staleness_history else None
        }
