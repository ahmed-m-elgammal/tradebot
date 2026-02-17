"""
Enhanced Base Ingestor with Retry and Rate Limiting

Base class for all data ingestors with infrastructure integration.
"""

import time
import pandas as pd
from abc import ABC, abstractmethod

from src.config import get_config
from src.utils.logger import get_logger
from src.utils.rate_limiter import RateLimiter
from src.utils.exceptions import DataIngestionError
from src.data.ingest.validator import DataValidator

logger = get_logger(__name__)


class BaseIngestor(ABC):
    """Enhanced base class for data ingestors."""

    def __init__(self):
        config = get_config()
        self.validator = DataValidator(fail_on_error=False, auto_fix=True)
        self.rate_limiter = RateLimiter(
            calls_per_minute=config.data.ingest.rate_limit.calls_per_minute,
            burst_size=config.data.ingest.rate_limit.burst_size
        )

        logger.info(f"{self.__class__.__name__} initialized", extra={
            'rate_limit_cpm': config.data.ingest.rate_limit.calls_per_minute,
            'burst_size': config.data.ingest.rate_limit.burst_size
        })

    @staticmethod
    def _enforce_idempotency(df: pd.DataFrame) -> pd.DataFrame:
        """Deduplicate and normalize ordering to make ingest idempotent."""
        if df.empty or 'timestamp' not in df.columns:
            return df

        pre_len = len(df)
        out = df.drop_duplicates(subset=['timestamp'], keep='last').sort_values('timestamp').reset_index(drop=True)
        dropped = pre_len - len(out)
        if dropped > 0:
            logger.warning("Dropped duplicate bars during ingest", extra={'dropped_duplicates': dropped})
        return out

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str, **kwargs) -> pd.DataFrame:
        """Fetch OHLCV data from source."""

    def load_and_validate(self, symbol: str, timeframe: str, **kwargs) -> pd.DataFrame:
        """Fetch and validate data with retry and rate limiting."""
        start_ts = time.perf_counter()
        try:
            df = self.fetch_ohlcv(symbol, timeframe, **kwargs)

            if df.empty:
                logger.warning(f"No data returned for {symbol}", extra={'symbol': symbol, 'timeframe': timeframe})
                return df

            df = self._enforce_idempotency(df)
            df = self.validator.clean_and_validate(df)

            logger.info(f"Successfully loaded and validated data for {symbol}", extra={
                'symbol': symbol,
                'timeframe': timeframe,
                'rows': len(df),
                'start': df['timestamp'].min(),
                'end': df['timestamp'].max(),
                'ingest_latency_seconds': time.perf_counter() - start_ts,
            })
            return df

        except Exception as e:
            logger.error(f"Failed to load data for {symbol}", extra={
                'symbol': symbol,
                'timeframe': timeframe,
                'error': str(e),
                'error_type': type(e).__name__,
                'ingest_latency_seconds': time.perf_counter() - start_ts,
            })
            raise DataIngestionError(f"Failed to load {symbol}: {e}") from e

    def get_rate_limiter_stats(self) -> dict:
        return self.rate_limiter.get_stats()
