"""
Unit Tests for Configuration System

Tests for Pydantic models, config loading, and validation.
"""

import sys
sys.path.insert(0, 'c:\\Users\\A-Dev\\Desktop\\Trading Bot')

import pytest
from pydantic import ValidationError
from src.config.settings import (
    Settings, RetryConfig, RateLimitConfig, RiskLimitsConfig,
    load_config, deep_merge
)


def test_retry_config_validation():
    """Test retry config validation."""
    # Valid config
    config = RetryConfig(max_attempts=3, base_delay=1.0, max_delay=60.0)
    assert config.max_attempts == 3
    assert config.base_delay == 1.0
    
    # Invalid: max_attempts out of range
    with pytest.raises(ValidationError):
        RetryConfig(max_attempts=0)  # Too low
    
    with pytest.raises(ValidationError):
        RetryConfig(max_attempts=20)  # Too high


def test_risk_limits_validation():
    """Test risk limits validation."""
    # Valid
    config = RiskLimitsConfig(max_position_size=0.05)
    assert config.max_position_size == 0.05
    
    # Invalid: out of range
    with pytest.raises(ValidationError):
        RiskLimitsConfig(max_position_size=0.5)  # Too high


def test_load_config():
    """Test config loading."""
    # Load dev config
    config = load_config('dev')
    assert config.environment == 'dev'
    assert config.logging.level == 'DEBUG'
    
    # Load prod config
    config = load_config('prod')
    assert config.environment == 'prod'
    assert config.risk.limits.max_position_size == 0.03  # More conservative


def test_deep_merge():
    """Test deep merge function."""
    base = {'a': 1, 'b': {'c': 2, 'd': 3}}
    override = {'b': {'d': 4}, 'e': 5}
    
    result = deep_merge(base, override)
    
    assert result['a'] == 1
    assert result['b']['c'] == 2
    assert result['b']['d'] == 4  # Overridden
    assert result['e'] == 5


def test_config_access():
    """Test config field access."""
    config = load_config('dev')
    
    # Nested access
    assert hasattr(config.data.ingest, 'retry')
    assert hasattr(config.data.ingest.retry, 'max_attempts')
    assert config.data.ingest.retry.max_attempts >= 1
    
    # Strategy config
    assert config.strategy.mean_reversion.rsi_window == 14
    assert 10 <= config.strategy.mean_reversion.rsi_oversold <= 40


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
