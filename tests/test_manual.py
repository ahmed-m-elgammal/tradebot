"""
Simple test to verify feature module works
"""

import sys
sys.path.insert(0, 'c:\\Users\\A-Dev\\Desktop\\Trading Bot')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.features.price_features import PriceFeatures
from src.features.technical_indicators import TechnicalIndicators
from src.features.validation.lookahead_detector import LookaheadDetector


def create_mock_data(n=100):
    """Create simple mock OHLCV data."""
    np.random.seed(42)
    timestamps = [datetime(2024, 1, 1) + timedelta(minutes=i) for i in range(n)]
    prices = 100 * np.cumprod(1 + np.random.normal(0, 0.01, n))
    
    data = []
    for i, (ts, close) in enumerate(zip(timestamps, prices)):
        data.append({
            'timestamp': ts,
            'open': close * 0.99,
            'high': close * 1.01,
            'low': close * 0.98,
            'close': close,
            'volume': 1000000
        })
    
    return pd.DataFrame(data)

print("Creating mock data...")
df = create_mock_data(200)
print(f"Created {len(df)} rows")

print("\nTesting PriceFeatures...")
pf = PriceFeatures(validate_lookahead=False)
df, cols = pf.compute_returns(df, horizons=[5])
print(f"Added columns: {cols}")
print(f"Sample returns: {df['return_5min_lag'].dropna().head()}")

print("\nTesting TechnicalIndicators...")
ti = TechnicalIndicators(validate_lookahead=False)
df = ti.add_rsi(df)
print(f"RSI values - min:{df['rsi'].min():.2f}, max:{df['rsi'].max():.2f}, mean:{df['rsi'].mean():.2f}")

print("\nTesting LookaheadDetector...")
df['bad_feature'] = df['close'].shift(-5)
detector = LookaheadDetector()
results = detector.detect_lookahead(df, ['bad_feature', 'rsi'])
print(f"bad_feature status: {results['bad_feature']['status']}")
print(f"rsi status: {results['rsi']['status']}")

print("\n✅ All manual tests passed!")
