"""
Feature Engineering Module

This module provides feature computation for trading strategies with built-in
prevention of lookahead bias.

Modules:
    - base_feature: Abstract base class for all features
    - price_features: Price-based features (returns, volatility, ratios)
    - technical_indicators: Technical indicators (RSI, MACD, Bollinger Bands)
    - feature_store: Caching layer for computed features
    - validation: Lookahead bias detection and feature health monitoring
"""

from src.features.base_feature import BaseFeature
from src.features.price_features import PriceFeatures
from src.features.technical_indicators import TechnicalIndicators

__all__ = [
    'BaseFeature',
    'PriceFeatures',
    'TechnicalIndicators',
]
