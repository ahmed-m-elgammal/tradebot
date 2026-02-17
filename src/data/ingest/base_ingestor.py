"""
Enhanced Base Ingestor with Retry and Rate Limiting

Base class for all data ingestors with infrastructure integration.
"""

import pandas as pd
from abc import ABC, abstractmethod
from typing import Optional
import sys
sys.path.insert(0, 'c:\\Users\\A-Dev\\Desktop\\Trading Bot')

from src.config import get_config
from src.utils.logger import get_logger
from src.utils.retry import retry_with_backoff
from src.utils.rate_limiter import RateLimiter
from src.utils.exceptions import DataIngestionError
from src.data.ingest.validator import DataValidator

logger = get_logger(__name__)


class BaseIngestor(ABC):
    """
    Enhanced base class for data ingestors.
    
    NEW FEATURES:
    - Integrated rate limiting
    - Automatic retry on failures
    - Structured logging
    - Data validation with cleaning
    """
    
    def __init__(self):
        """Initialize base ingestor with infrastructure."""
        # Load configuration
        config = get_config()
        
        # Initialize validator
        self.validator = DataValidator(fail_on_error=False, auto_fix=True)
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            calls_per_minute=config.data.ingest.rate_limit.calls_per_minute,
            burst_size=config.data.ingest.rate_limit.burst_size
        )
        
        logger.info(f"{self.__class__.__name__} initialized", extra={
            'rate_limit_cpm': config.data.ingest.rate_limit.calls_per_minute,
            'burst_size': config.data.ingest.rate_limit.burst_size
        })
    
    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str, **kwargs) -> pd.DataFrame:
        """
        Fetch OHLCV data from source.
        
        Must be implemented by subclasses.
        Should use @retry_with_backoff decorator.
        Should call self.rate_limiter.acquire() before API calls.
        """
        pass
    
    def load_and_validate(self, symbol: str, timeframe: str, **kwargs) -> pd.DataFrame:
        """
        Fetch and validate data with retry and rate limiting.
        
        Args:
            symbol: Trading symbol
            timeframe: Data timeframe
            **kwargs: Additional arguments for fetch_ohlcv
            
        Returns:
            Validated DataFrame
            
        Raises:
            DataIngestionError: On fatal errors
        """
        try:
            # Fetch data (subclass implementation handles retry and rate limiting)
            df = self.fetch_ohlcv(symbol, timeframe, **kwargs)
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}", extra={
                    'symbol': symbol,
                    'timeframe': timeframe
                })
                return df
            
            # Clean and validate
            df = self.validator.clean_and_validate(df)
            
            logger.info(f"Successfully loaded and validated data for {symbol}", extra={
                'symbol': symbol,
                'timeframe': timeframe,
                'rows': len(df),
                'start': df['timestamp'].min(),
                'end': df['timestamp'].max()
            })
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load data for {symbol}", extra={
                'symbol': symbol,
                'timeframe': timeframe,
                'error': str(e),
                'error_type': type(e).__name__
            })
            raise DataIngestionError(f"Failed to load {symbol}: {e}") from e
    
    def get_rate_limiter_stats(self) -> dict:
        """Get rate limiter statistics."""
        return self.rate_limiter.get_stats()
