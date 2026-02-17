"""
Custom Exception Types

Specific exceptions for different error scenarios.
"""


class TradingBotError(Exception):
    """Base exception for trading bot."""
    pass


class DataIngestionError(TradingBotError):
    """Error during data ingestion."""
    pass


class DataValidationError(TradingBotError):
    """Data failed validation."""
    pass


class RateLimitError(TradingBotError):
    """Rate limit exceeded."""
    pass


class StorageError(TradingBotError):
    """Error writing/reading storage."""
    pass


class ConfigurationError(TradingBotError):
    """Invalid configuration."""
    pass


class StrategyError(TradingBotError):
    """Error in strategy execution."""
    pass


class RiskViolationError(TradingBotError):
    """Risk limit violated."""
    pass
