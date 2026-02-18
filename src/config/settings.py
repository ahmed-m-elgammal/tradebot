"""
Settings and Configuration Management

Pydantic models for type-safe configuration with validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Optional
import yaml
import os
from pathlib import Path


class RetryConfig(BaseModel):
    """Retry configuration for API calls."""
    max_attempts: int = Field(3, ge=1, le=10, description="Maximum retry attempts")
    base_delay: float = Field(1.0, ge=0.1, description="Base delay in seconds")
    max_delay: float = Field(60.0, ge=1.0, description="Maximum delay cap")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    calls_per_minute: int = Field(60, ge=1, description="Max calls per minute")
    burst_size: int = Field(10, ge=1, description="Burst allowance")


class IngestConfig(BaseModel):
    """Data ingestion configuration."""
    retry: RetryConfig = RetryConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()


class StorageConfig(BaseModel):
    """Storage configuration."""
    compression: str = Field('snappy', description="Parquet compression algorithm")
    validate_schema: bool = Field(True, description="Enforce schema validation")
    metadata_tracking: bool = Field(True, description="Track file metadata")


class QualityConfig(BaseModel):
    """Data quality configuration."""
    outlier_thresholds: Dict[str, float] = Field(
        default={'crypto': 0.15, 'equity': 0.10},
        description="Outlier detection thresholds by asset class"
    )
    staleness_limits: Dict[str, int] = Field(
        default={'live': 60, 'minute': 300, 'daily': 86400},
        description="Staleness limits in seconds by data type"
    )


class DataConfig(BaseModel):
    """Data pipeline configuration."""
    ingest: IngestConfig = IngestConfig()
    storage: StorageConfig = StorageConfig()
    quality: QualityConfig = QualityConfig()


class RiskLimitsConfig(BaseModel):
    """Risk limit configuration."""
    max_position_size: float = Field(0.05, ge=0.01, le=0.2, description="Max position size as fraction of equity")
    max_portfolio_heat: float = Field(0.10, ge=0.01, le=0.5, description="Max total portfolio risk")
    max_drawdown: float = Field(0.15, ge=0.05, le=0.5, description="Max drawdown before halt")
    daily_loss_limit: float = Field(0.03, ge=0.01, le=0.2, description="Daily loss limit")
    max_symbol_exposure: float = Field(0.05, ge=0.01, le=0.5, description="Max exposure per symbol")
    max_correlated_exposure: float = Field(0.20, ge=0.05, le=1.0, description="Max exposure in correlated basket")
    correlation_threshold: float = Field(0.8, ge=0.5, le=1.0, description="Correlation threshold for grouping")
    max_sector_exposure: float = Field(0.30, ge=0.05, le=1.0, description="Max sector exposure")
    max_cluster_exposure: float = Field(0.25, ge=0.05, le=1.0, description="Max cluster exposure")


class RiskConfig(BaseModel):
    """Risk management configuration."""
    limits: RiskLimitsConfig = RiskLimitsConfig()


class MeanReversionStrategyConfig(BaseModel):
    """Mean reversion strategy configuration."""
    bollinger_window: int = Field(20, ge=5, le=100, description="Bollinger Bands window")
    bollinger_std: float = Field(2.0, ge=1.0, le=4.0, description="Bollinger Bands std dev")
    rsi_window: int = Field(14, ge=2, le=50, description="RSI window")
    rsi_oversold: int = Field(30, ge=10, le=40, description="RSI oversold threshold")
    rsi_overbought: int = Field(70, ge=60, le=90, description="RSI overbought threshold")
    long_only: bool = Field(True, description="Use long-only lifecycle in Phase 1")
    stop_loss_pct: float = Field(0.05, ge=0.0, le=0.2, description="Emergency stop loss percentage")
    max_bars_in_trade: int = Field(0, ge=0, le=10000, description="Time stop in bars, 0 disables")
    atr_stop_mult: float = Field(0.0, ge=0.0, le=10.0, description="ATR multiple for stop placement")
    volatility_kill_switch: float = Field(0.0, ge=0.0, le=1.0, description="ATR/close threshold to flatten positions")


class StrategyConfig(BaseModel):
    """Trading strategy configuration."""
    mean_reversion: MeanReversionStrategyConfig = MeanReversionStrategyConfig()


class BacktestConfig(BaseModel):
    """Backtesting configuration."""
    initial_capital: float = Field(10000, ge=1000, description="Starting capital")
    commission_pct: float = Field(0.001, ge=0, le=0.01, description="Commission percentage")
    slippage_pct: float = Field(0.002, ge=0, le=0.01, description="Slippage percentage")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field('INFO', description="Log level")
    format: str = Field('json', description="Log format (json or text)")
    file: str = Field('logs/trading_bot.log', description="Log file path")
    max_bytes: int = Field(10485760, ge=1024, description="Max log file size")
    backup_count: int = Field(5, ge=1, le=20, description="Number of backup log files")
    console: bool = Field(True, description="Log to console")
    
    @validator('level')
    def validate_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = ['json', 'text']
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid log format: {v}. Must be one of {valid_formats}")
        return v.lower()


class Settings(BaseModel):
    """Main configuration settings."""
    environment: str = Field('dev', description="Environment name")
    data: DataConfig = DataConfig()
    risk: RiskConfig = RiskConfig()
    strategy: StrategyConfig = StrategyConfig()
    backtest: BacktestConfig = BacktestConfig()
    logging: LoggingConfig = LoggingConfig()
    
    class Config:
        validate_assignment = True  # Validate on attribute assignment


def load_config(env: Optional[str] = None) -> Settings:
    """
    Load configuration from YAML files.
    
    Loads base.yaml and merges environment-specific overrides.
    
    Args:
        env: Environment name ('dev', 'prod'). Default from ENV variable or 'dev'
        
    Returns:
        Validated Settings object
        
    Raises:
        FileNotFoundError: If config files not found
        ValidationError: If configuration is invalid
    """
    # Determine environment
    if env is None:
        env = os.getenv('TRADING_BOT_ENV', 'dev')
    
    # Find config directory
    # Try relative to current working directory first
    config_dir = Path('config')
    if not config_dir.exists():
        # Try relative to this file (for installed packages)
        config_dir = Path(__file__).parent.parent.parent / 'config'
    
    if not config_dir.exists():
        raise FileNotFoundError(f"Config directory not found: {config_dir}")
    
    # Load base config
    base_file = config_dir / 'base.yaml'
    if not base_file.exists():
        raise FileNotFoundError(f"Base config not found: {base_file}")
    
    with open(base_file) as f:
        config = yaml.safe_load(f)
    
    # Load environment-specific overrides
    env_file = config_dir / f'{env}.yaml'
    if env_file.exists():
        with open(env_file) as f:
            env_config = yaml.safe_load(f)
            config = deep_merge(config, env_config)
    
    # Create and validate Settings object
    return Settings(**config)


def deep_merge(base: dict, override: dict) -> dict:
    """
    Deep merge two dictionaries.
    
    Args:
        base: Base dictionary
        override: Override values
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


# Global config instance (lazy loaded)
_config: Optional[Settings] = None


def get_config() -> Settings:
    """
    Get global config instance (singleton pattern).
    
    Returns:
        Settings instance
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config
