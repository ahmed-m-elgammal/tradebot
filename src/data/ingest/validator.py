"""
Enhanced Data Validator with Logging and Robust Handling

Handles duplicates, unsorted data, and provides detailed logging.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Union, Tuple
import sys
sys.path.insert(0, 'c:\\Users\\A-Dev\\Desktop\\Trading Bot')

from src.config import get_config
from src.utils.logger import get_logger
from src.utils.exceptions import DataValidationError

logger = get_logger(__name__)


class DataValidator:
    """
    Enhanced validator with duplicate/unsorted handling and logging.
    
    NEW FEATURES:
    - Detects and removes duplicate timestamps
    - Detects and sorts unsorted timestamps
    - Structured logging for all validations
    - Configurable thresholds from config
    """
    
    REQUIRED_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    
    def __init__(self, fail_on_error: bool = True, auto_fix: bool = True):
        """
        Initialize validator.
        
        Args:
            fail_on_error: Raise exception on validation failure
            auto_fix: Automatically fix fixable issues (duplicates, sorting)
        """
        self.fail_on_error = fail_on_error
        self.auto_fix = auto_fix
        
        # Load config
        try:
            config = get_config()
            self.max_delay_minutes = config.data.quality.staleness_threshold_minutes
        except:
            self.max_delay_minutes = 15
            
        logger.info("DataValidator initialized", extra={
            'fail_on_error': fail_on_error,
            'auto_fix': auto_fix,
            'max_delay_minutes': self.max_delay_minutes
        })
    
    def validate_schema(self, df: pd.DataFrame) -> bool:
        """Checks if DataFrame contains all required columns."""
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        
        if missing:
            logger.error("Schema validation failed", extra={
                'missing_columns': missing,
                'present_columns': list(df.columns)
            })
            
            if self.fail_on_error:
                raise DataValidationError(f"Missing required columns: {missing}")
            return False
        
        logger.debug("Schema validation passed")
        return True
    
    def validate_ranges(self, df: pd.DataFrame) -> bool:
        """Checks if OHLCV values are within logical ranges."""
        errors = []
        
        # Check for empty DataFrame
        if df.empty:
            logger.warning("Empty DataFrame provided for range validation")
            return True
        
        # Price > 0
        if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
            errors.append("Found non-positive prices")
            
        # High >= Low
        if (df['high'] < df['low']).any():
            errors.append("Found High < Low")
            
        # High >= Open and High >= Close
        if (df['high'] < df['open']).any() or (df['high'] < df['close']).any():
            errors.append("Found High < Open or High < Close")

        # Low <= Open and Low <= Close
        if (df['low'] > df['open']).any() or (df['low'] > df['close']).any():
            errors.append("Found Low > Open or Low > Close")
            
        # Volume >= 0
        if (df['volume'] < 0).any():
            errors.append("Found negative volume")

        if errors:
            logger.error("Range validation failed", extra={
                'errors': errors,
                'num_rows': len(df)
            })
            
            if self.fail_on_error:
                raise DataValidationError(f"Range validation failed: {'; '.join(errors)}")
            return False
        
        logger.debug("Range validation passed")
        return True
    
    def check_duplicates(self, df: pd.DataFrame) -> Tuple[bool, pd.DataFrame]:
        """
        Check for and optionally remove duplicate timestamps.
        
        Returns:
            (has_duplicates, cleaned_df)
        """
        duplicates = df['timestamp'].duplicated().sum()
        
        if duplicates > 0:
            logger.warning(f"Found {duplicates} duplicate timestamps", extra={
                'duplicate_count': duplicates,
                'total_rows': len(df)
            })
            
            if self.auto_fix:
                # Keep last occurrence
                df_clean = df.drop_duplicates(subset=['timestamp'], keep='last')
                logger.info(f"Removed {duplicates} duplicates", extra={
                    'removed_count': duplicates,
                    'rows_before': len(df),
                    'rows_after': len(df_clean)
                })
                return True, df_clean
            
            return True, df
        
        return False, df
    
    def check_sorted(self, df: pd.DataFrame) -> Tuple[bool, pd.DataFrame]:
        """
        Check if timestamps are sorted and optionally sort them.
        
        Returns:
            (is_unsorted, sorted_df)
        """
        if df.empty:
            return False, df
        
        is_sorted = df['timestamp'].is_monotonic_increasing
        
        if not is_sorted:
            logger.warning("Timestamps are not sorted", extra={
                'num_rows': len(df)
            })
            
            if self.auto_fix:
                df_sorted = df.sort_values('timestamp').reset_index(drop=True)
                logger.info("Sorted timestamps", extra={
                    'num_rows': len(df)
                })
                return True, df_sorted
            
            return True, df
        
        return False, df
    
    def validate_staleness(self, df: pd.DataFrame, max_delay_minutes: Optional[int] = None) -> bool:
        """Checks if the data is too old."""
        if df.empty:
            logger.debug("Empty DataFrame, skipping staleness check")
            return True
        
        max_delay = max_delay_minutes or self.max_delay_minutes
            
        # Ensure timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            except Exception as e:
                logger.error("Timestamp column is not convertible to datetime", extra={
                    'error': str(e)
                })
                if self.fail_on_error:
                    raise DataValidationError("Timestamp column is not convertible to datetime")
                return False

        last_timestamp = df['timestamp'].max()
        
        # Convert to UTC if timezone aware, else assume UTC
        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
        else:
            last_timestamp = last_timestamp.tz_convert('UTC')
              
        now = datetime.now(timezone.utc)
        time_diff = now - last_timestamp
        
        if time_diff > timedelta(minutes=max_delay):
            logger.warning("Data is stale", extra={
                'last_timestamp': last_timestamp.isoformat(),
                'current_time': now.isoformat(),
                'age_minutes': time_diff.total_seconds() / 60,
                'threshold_minutes': max_delay
            })
            
            if self.fail_on_error:
                raise DataValidationError(f"Data is stale. Last timestamp: {last_timestamp}, Age: {time_diff}")
            return False
            
        logger.debug("Staleness check passed", extra={
            'age_minutes': time_diff.total_seconds() / 60
        })
        return True
    
    def validate_ohlcv(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Comprehensive OHLCV validation.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            if not self.validate_schema(df):
                errors.append("Schema validation failed")
            
            if not self.validate_ranges(df):
                errors.append("Range validation failed")
                
        except DataValidationError as e:
            errors.append(str(e))
        
        is_valid = len(errors) == 0
        
        logger.info("OHLCV validation complete", extra={
            'is_valid': is_valid,
            'num_errors': len(errors),
            'num_rows': len(df)
        })
        
        return is_valid, errors
    
    def clean_and_validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean data (remove duplicates, sort) and validate.
        
        Returns:
            Cleaned and validated DataFrame
            
        Raises:
            DataValidationError: If validation fails
        """
        if df.empty:
            logger.warning("Empty DataFrame provided")
            return df
        
        original_len = len(df)
        
        # Check and fix duplicates
        has_dups, df = self.check_duplicates(df)
        
        # Check and fix sorting
        is_unsorted, df = self.check_sorted(df)
        
        # Validate schema
        if not self.validate_schema(df):
            raise DataValidationError("Schema validation failed")
        
        # Validate ranges
        if not self.validate_ranges(df):
            raise DataValidationError("Range validation failed")
        
        final_len = len(df)
        
        if final_len != original_len:
            logger.info("Data cleaned", extra={
                'original_rows': original_len,
                'final_rows': final_len,
                'rows_removed': original_len - final_len
            })
        
        return df
    
    def validate(self, df: pd.DataFrame) -> bool:
        """Runs all validation checks (legacy method)."""
        try:
            return (self.validate_schema(df) and 
                    self.validate_ranges(df) and 
                    self.validate_staleness(df))
        except DataValidationError as e:
            if self.fail_on_error:
                raise e
            return False
