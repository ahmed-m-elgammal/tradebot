"""Enhanced Data Validator with logging and robust handling."""

import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Tuple

from src.config import get_config
from src.utils.logger import get_logger
from src.utils.exceptions import DataValidationError

logger = get_logger(__name__)


class DataValidator:
    """Validator with duplicate/sorting handling and validation reporting."""

    REQUIRED_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

    def __init__(self, fail_on_error: bool = True, auto_fix: bool = True):
        self.fail_on_error = fail_on_error
        self.auto_fix = auto_fix
        self.last_report: Dict = {
            'duplicates_removed': 0,
            'sorting_fixes': 0,
            'range_errors': 0,
            'schema_errors': 0,
            'staleness_errors': 0,
        }

        try:
            config = get_config()
            self.max_delay_minutes = config.data.quality.staleness_limits.get('minute', 300) / 60
        except Exception:
            self.max_delay_minutes = 15

    def _reset_report(self) -> None:
        self.last_report = {
            'duplicates_removed': 0,
            'sorting_fixes': 0,
            'range_errors': 0,
            'schema_errors': 0,
            'staleness_errors': 0,
        }

    def get_last_report(self) -> Dict:
        return dict(self.last_report)

    def validate_schema(self, df: pd.DataFrame) -> bool:
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            self.last_report['schema_errors'] += 1
            if self.fail_on_error:
                raise DataValidationError(f"Missing required columns: {missing}")
            return False
        return True

    def validate_ranges(self, df: pd.DataFrame) -> bool:
        if df.empty:
            return True

        errors = []
        if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
            errors.append("Found non-positive prices")
        if (df['high'] < df['low']).any():
            errors.append("Found High < Low")
        if (df['high'] < df['open']).any() or (df['high'] < df['close']).any():
            errors.append("Found High < Open or High < Close")
        if (df['low'] > df['open']).any() or (df['low'] > df['close']).any():
            errors.append("Found Low > Open or Low > Close")
        if (df['volume'] < 0).any():
            errors.append("Found negative volume")

        if errors:
            self.last_report['range_errors'] += len(errors)
            if self.fail_on_error:
                raise DataValidationError(f"Range validation failed: {'; '.join(errors)}")
            return False
        return True

    def check_duplicates(self, df: pd.DataFrame) -> Tuple[bool, pd.DataFrame]:
        duplicates = df['timestamp'].duplicated().sum()
        if duplicates > 0:
            if self.auto_fix:
                df_clean = df.drop_duplicates(subset=['timestamp'], keep='last')
                self.last_report['duplicates_removed'] += int(duplicates)
                return True, df_clean
            return True, df
        return False, df

    def check_sorted(self, df: pd.DataFrame) -> Tuple[bool, pd.DataFrame]:
        is_sorted = df['timestamp'].is_monotonic_increasing
        if not is_sorted:
            if self.auto_fix:
                self.last_report['sorting_fixes'] += 1
                return True, df.sort_values('timestamp').reset_index(drop=True)
            return True, df
        return False, df

    def validate_staleness(self, df: pd.DataFrame, max_delay_minutes: Optional[int] = None) -> bool:
        if df.empty:
            return True

        max_delay = max_delay_minutes or self.max_delay_minutes
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            except Exception:
                self.last_report['staleness_errors'] += 1
                if self.fail_on_error:
                    raise DataValidationError("Timestamp column is not convertible to datetime")
                return False

        last_timestamp = df['timestamp'].max()
        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
        else:
            last_timestamp = last_timestamp.tz_convert('UTC')

        now = datetime.now(timezone.utc)
        if now - last_timestamp > timedelta(minutes=max_delay):
            self.last_report['staleness_errors'] += 1
            if self.fail_on_error:
                raise DataValidationError(f"Data is stale. Last timestamp: {last_timestamp}")
            return False
        return True

    def validate_ohlcv(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        errors = []
        try:
            if not self.validate_schema(df):
                errors.append("Schema validation failed")
            if not self.validate_ranges(df):
                errors.append("Range validation failed")
        except DataValidationError as e:
            errors.append(str(e))
        return len(errors) == 0, errors

    def clean_and_validate(self, df: pd.DataFrame) -> pd.DataFrame:
        self._reset_report()
        if df.empty:
            return df

        _, df = self.check_duplicates(df)
        _, df = self.check_sorted(df)

        if not self.validate_schema(df):
            raise DataValidationError("Schema validation failed")
        if not self.validate_ranges(df):
            raise DataValidationError("Range validation failed")

        return df

    def validate(self, df: pd.DataFrame) -> bool:
        try:
            return (self.validate_schema(df) and
                    self.validate_ranges(df) and
                    self.validate_staleness(df))
        except DataValidationError:
            if self.fail_on_error:
                raise
            return False
