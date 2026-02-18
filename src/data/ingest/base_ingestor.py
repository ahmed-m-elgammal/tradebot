"""Enhanced Base Ingestor with retry, rate-limiting, and observability."""

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
        self.metrics = {
            'requests_total': 0,
            'requests_failed': 0,
            'duplicates_dropped': 0,
            'validator_sort_fixes': 0,
            'validator_schema_errors': 0,
            'validator_range_errors': 0,
            'validator_staleness_errors': 0,
            'retryable_errors': 0,
            'non_retryable_errors': 0,
            'total_latency_seconds': 0.0,
        }
        self.heartbeat_every = 10

    def _heartbeat(self) -> None:
        if self.metrics['requests_total'] % self.heartbeat_every != 0:
            return
        avg_latency = (self.metrics['total_latency_seconds'] / self.metrics['requests_total']
                       if self.metrics['requests_total'] else 0.0)
        logger.info("Ingest heartbeat", extra={
            'requests_total': self.metrics['requests_total'],
            'requests_failed': self.metrics['requests_failed'],
            'duplicates_dropped': self.metrics['duplicates_dropped'],
            'validator_sort_fixes': self.metrics['validator_sort_fixes'],
            'validator_schema_errors': self.metrics['validator_schema_errors'],
            'validator_range_errors': self.metrics['validator_range_errors'],
            'validator_staleness_errors': self.metrics['validator_staleness_errors'],
            'retryable_errors': self.metrics['retryable_errors'],
            'non_retryable_errors': self.metrics['non_retryable_errors'],
            'avg_latency_seconds': avg_latency,
        })

    @staticmethod
    def _enforce_idempotency(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        if df.empty or 'timestamp' not in df.columns:
            return df, 0
        pre_len = len(df)
        out = df.drop_duplicates(subset=['timestamp'], keep='last').sort_values('timestamp').reset_index(drop=True)
        return out, pre_len - len(out)

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str, **kwargs) -> pd.DataFrame:
        """Fetch OHLCV data from source."""

    def load_and_validate(self, symbol: str, timeframe: str, **kwargs) -> pd.DataFrame:
        start_ts = time.perf_counter()
        self.metrics['requests_total'] += 1
        try:
            df = self.fetch_ohlcv(symbol, timeframe, **kwargs)
            if df.empty:
                logger.warning(f"No data returned for {symbol}", extra={'symbol': symbol, 'timeframe': timeframe})
                return df

            df, dropped = self._enforce_idempotency(df)
            self.metrics['duplicates_dropped'] += dropped

            df = self.validator.clean_and_validate(df)
            report = self.validator.get_last_report()
            self.metrics['duplicates_dropped'] += report['duplicates_removed']
            self.metrics['validator_sort_fixes'] += report['sorting_fixes']
            self.metrics['validator_schema_errors'] += report['schema_errors']
            self.metrics['validator_range_errors'] += report['range_errors']
            self.metrics['validator_staleness_errors'] += report['staleness_errors']

            latency = time.perf_counter() - start_ts
            self.metrics['total_latency_seconds'] += latency

            logger.info(f"Successfully loaded and validated data for {symbol}", extra={
                'symbol': symbol,
                'timeframe': timeframe,
                'rows': len(df),
                'start': df['timestamp'].min(),
                'end': df['timestamp'].max(),
                'ingest_latency_seconds': latency,
                'dropped_duplicates': dropped,
                'validator_report': report,
            })
            self._heartbeat()
            return df

        except Exception as e:
            latency = time.perf_counter() - start_ts
            self.metrics['total_latency_seconds'] += latency
            self.metrics['requests_failed'] += 1
            err_name = type(e).__name__
            if 'Network' in err_name or 'Timeout' in err_name:
                self.metrics['retryable_errors'] += 1
            else:
                self.metrics['non_retryable_errors'] += 1

            logger.error(f"Failed to load data for {symbol}", extra={
                'symbol': symbol,
                'timeframe': timeframe,
                'error': str(e),
                'error_type': err_name,
                'ingest_latency_seconds': latency,
                'metrics_snapshot': self.get_ingest_metrics(),
            })
            self._heartbeat()
            raise DataIngestionError(f"Failed to load {symbol}: {e}") from e

    def get_rate_limiter_stats(self) -> dict:
        return self.rate_limiter.get_stats()

    def get_ingest_metrics(self) -> dict:
        avg_latency = (self.metrics['total_latency_seconds'] / self.metrics['requests_total']
                       if self.metrics['requests_total'] else 0.0)
        return {**self.metrics, 'avg_latency_seconds': avg_latency}
