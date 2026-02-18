"""Negative-path tests for ingestion and config boundaries."""

import pytest
import pandas as pd

pydantic = pytest.importorskip('pydantic')

from src.data.ingest.validator import DataValidator
from src.config.settings import RiskLimitsConfig, MeanReversionStrategyConfig


def test_validator_rejects_malformed_timestamp_when_no_autofix():
    validator = DataValidator(fail_on_error=False, auto_fix=False)
    df = pd.DataFrame({
        'timestamp': ['bad-ts', 'also-bad'],
        'open': [1, 1], 'high': [2, 2], 'low': [0.5, 0.5], 'close': [1, 1], 'volume': [10, 10],
    })
    assert validator.validate_staleness(df, max_delay_minutes=1) is False


def test_validator_dedupes_duplicate_burst_and_reports():
    validator = DataValidator(fail_on_error=False, auto_fix=True)
    df = pd.DataFrame({
        'timestamp': [
            pd.Timestamp('2024-01-01 00:00:00'),
            pd.Timestamp('2024-01-01 00:00:00'),
            pd.Timestamp('2024-01-01 00:00:00'),
            pd.Timestamp('2024-01-01 00:01:00'),
        ],
        'open': [1, 1, 1, 1], 'high': [2, 2, 2, 2], 'low': [0.5, 0.5, 0.5, 0.5], 'close': [1, 1, 1, 1], 'volume': [10, 10, 10, 10],
    })
    cleaned = validator.clean_and_validate(df)
    report = validator.get_last_report()

    assert len(cleaned) == 2
    assert report['duplicates_removed'] == 2


def test_risk_config_boundaries_new_fields():
    with pytest.raises(Exception):
        RiskLimitsConfig(max_symbol_exposure=1.5)

    with pytest.raises(Exception):
        RiskLimitsConfig(correlation_threshold=0.1)

    with pytest.raises(Exception):
        MeanReversionStrategyConfig(atr_stop_mult=-1.0)
