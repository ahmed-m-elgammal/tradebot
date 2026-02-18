"""
Enhanced CCXT Crypto Ingestor with Infrastructure

Integrated retry logic, rate limiting, and structured logging.
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List

from src.data.ingest.base_ingestor import BaseIngestor
from src.data.ingest.validator import DataValidator
from src.config import get_config
from src.utils.logger import get_logger
from src.utils.retry import retry_with_backoff
from src.utils.rate_limiter import RateLimiter
from src.utils.exceptions import DataIngestionError

logger = get_logger(__name__)


class CCXTCryptoIngestor(BaseIngestor):
    """
    Ingest cryptocurrency data from CCXT exchanges.
    
    NOW WITH:
    - Automatic retry on transient failures
    - Rate limiting to prevent API bans
    - Structured logging for monitoring
    - Proper error handling and classification
    """
    
    def __init__(self, exchange_name: str = 'binance'):
        """
        Initialize CCXT ingestor.
        
        Args:
            exchange_name: Name of exchange ('binance', 'coinbase', etc.)
        """
        try:
            exchange_class = getattr(ccxt, exchange_name)
            self.exchange = exchange_class({'enableRateLimit': True})
            self.exchange_name = exchange_name
            
            # Load configuration
            config = get_config()
            self.validator = DataValidator()
            
            # Set up rate limiter from config
            self.rate_limiter = RateLimiter(
                calls_per_minute=config.data.ingest.rate_limit.calls_per_minute,
                burst_size=config.data.ingest.rate_limit.burst_size
            )
            
            logger.info(f"Initialized CCXT ingestor for {exchange_name}", extra={
                'exchange': exchange_name,
                'rate_limit': config.data.ingest.rate_limit.calls_per_minute
            })
            
        except Exception as e:
            logger.error(f"Failed to initialize CCXT exchange {exchange_name}", extra={
                'exchange': exchange_name,
                'error': str(e)
            })
            raise DataIngestionError(f"Failed to initialize exchange: {e}") from e
    
    @retry_with_backoff(
        max_attempts=3,
        base_delay=1.0,
        exceptions=(ccxt.NetworkError, ccxt.ExchangeNotAvailable)
    )
    def fetch_ohlcv(self, 
                    symbol: str,
                    timeframe: str = '1m',
                    since: Optional[datetime] = None,
                    limit: int = 1000) -> pd.DataFrame:
        """
        Fetch OHLCV data with retry and rate limiting.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USD')
            timeframe: Candle timeframe ('1m', '5m', '1h', '1d')
            since: Start date (None for recent data)
            limit: Number of candles
            
        Returns:
            DataFrame with OHLCV data
            
        Raises:
            DataIngestionError: On fatal errors
        """
        # Apply rate limiting
        self.rate_limiter.acquire()
        
        try:
            # Convert datetime to timestamp
            since_ts = int(since.timestamp() * 1000) if since else None
            
            logger.debug(f"Fetching {symbol} {timeframe}  data", extra={
                'symbol': symbol,
                'timeframe': timeframe,
                'since': since,
                'limit': limit
            })
            
            # Fetch from exchange
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since_ts,
                limit=limit
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp from milliseconds
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Remove duplicates (from pagination)
            df = df.drop_duplicates(subset=['timestamp'], keep='last')
            
            # Sort chronologically
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Validate
            is_valid, errors = self.validator.validate_ohlcv(df)
            if not is_valid:
                logger.warning(f"Validation failed for {symbol}", extra={
                    'symbol': symbol,
                    'errors': errors
                })
            
            logger.info(f"Fetched {len(df)} bars for {symbol}", extra={
                'symbol': symbol,
                'bars': len(df),
                'timeframe': timeframe,
                'start': df['timestamp'].min(),
                'end': df['timestamp'].max()
            })
            
            return df
            
        except ccxt.ExchangeError as e:
            # Exchange-specific error (bad symbol, etc.)
            logger.error(f"Exchange error fetching {symbol}", extra={
                'symbol': symbol,
                'error': str(e),
                'error_type': 'ExchangeError'
            })
            raise DataIngestionError(f"Exchange error: {e}") from e
            
        except ccxt.NetworkError as e:
            # Network error - will be retried by decorator
            logger.warning(f"Network error fetching {symbol} (will retry)", extra={
                'symbol': symbol,
                'error': str(e),
                'error_type': 'NetworkError'
            })
            raise  # Let retry decorator handle it
            
        except Exception as e:
            # Unknown error
            logger.error(f"Unexpected error fetching {symbol}", extra={
                'symbol': symbol,
                'error': str(e),
                'error_type': type(e).__name__
            })
            raise DataIngestionError(f"Unexpected error: {e}") from e
    
    def get_rate_limiter_stats(self) -> dict:
        """Get rate limiter statistics."""
        return self.rate_limiter.get_stats()
