"""
Unit Tests for Feature Engineering Module

Tests for price features, technical indicators, and lookahead bias detection.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.features.price_features import PriceFeatures
from src.features.technical_indicators import TechnicalIndicators
from src.features.validation.lookahead_detector import LookaheadDetector


def create_mock_ohlcv(n_rows=100, start_price=100, volatility=0.02):
    """
    Create mock OHLCV data for testing.
    
    Args:
        n_rows: Number of rows to generate
        start_price: Starting price
        volatility: Price volatility (std dev of returns)
        
    Returns:
        DataFrame with OHLCV data
    """
    np.random.seed(42)
    
    # Generate timestamps
    start_time = datetime(2024, 1, 1)
    timestamps = [start_time + timedelta(minutes=i) for i in range(n_rows)]
    
    # Generate price series (random walk with drift)
    returns = np.random.normal(0.0001, volatility, n_rows)
    prices = start_price * np.cumprod(1 + returns)
    
    # Generate OHLC from close prices
    data = []
    for i, (ts, close) in enumerate(zip(timestamps, prices)):
        # Random high/low around close
        high = close * (1 + abs(np.random.normal(0, volatility/2)))
        low = close * (1 - abs(np.random.normal(0, volatility/2)))
        open_price = prices[i-1] if i > 0 else close
        volume = np.random.uniform(1000000, 5000000)
        
        data.append({
            'timestamp': ts,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    return df


class TestPriceFeatures:
    """Tests for PriceFeatures class."""
    
    def test_compute_returns(self):
        """Test return calculation is correct."""
        df = create_mock_ohlcv(200)
        features = PriceFeatures(validate_lookahead=False)
        
        df, cols = features.compute_returns(df, horizons=[5, 15])
        
        # Check columns created
        assert 'target_return_5min' in df.columns
        assert 'target_return_15min' in df.columns
        assert 'return_5min_lag' in df.columns
        assert 'return_15min_lag' in df.columns
        
        # Verify calculation is correct for target returns
        expected_5 = df['close'].pct_change(5).shift(-5)
        assert np.allclose(df['target_return_5min'], expected_5, equal_nan=True)
        
        # Verify calculation is correct for lagged returns
        expected_lag = df['close'].pct_change(5)
        assert np.allclose(df['return_5min_lag'], expected_lag, equal_nan=True)
    
    def test_compute_volatility(self):
        """Test volatility calculation."""
        df = create_mock_ohlcv(200)
        features = PriceFeatures(validate_lookahead=False)
        
        df, cols = features.compute_volatility(df, windows=[20])
        
        # Check columns created
        assert 'volatility_20' in df.columns
        assert 'parkinson_vol_20' in df.columns
        
        # Volatility should be positive
        assert (df['volatility_20'].dropna() > 0).all()
        
        # Should have NaN for first window-1 rows
        assert df['volatility_20'].iloc[:19].isna().all()
    
    def test_compute_price_ratios(self):
        """Test price ratio features."""
        df = create_mock_ohlcv(250)
        features = PriceFeatures(validate_lookahead=False)
        
        df, cols = features.compute_price_ratios(df)
        
        # Check columns created
        assert 'price_to_sma20' in df.columns
        assert 'price_to_sma50' in df.columns
        assert 'sma20_to_sma50' in df.columns
        
        # Price ratios should be around 1.0 (price near average)
        ratios = df['price_to_sma20'].dropna()
        assert ratios.mean() > 0.9 and ratios.mean() < 1.1
    
    def test_no_lookahead_in_lag_features(self):
        """Test that lagged features don't have lookahead bias."""
        df = create_mock_ohlcv(1000)
        features = PriceFeatures(validate_lookahead=False)
        
        df, cols = features.compute_returns(df, horizons=[5])
        
        # Only check lagged feature (not target)
        detector = LookaheadDetector(correlation_threshold=0.7)
        results = detector.detect_lookahead(df, ['return_5min_lag'])
        
        # Should pass (correlation with future should be low)
        assert results['return_5min_lag']['status'] in ['PASS', 'WARNING']
    
    def test_target_returns_have_lookahead(self):
        """Test that target returns correctly identified as having lookahead."""
        df = create_mock_ohlcv(1000)
        features = PriceFeatures(validate_lookahead=False)
        
        df, cols = features.compute_returns(df, horizons=[5])
        
        # Target returns SHOULD have lookahead (they use future data)
        detector = LookaheadDetector(correlation_threshold=0.7)
        results = detector.detect_lookahead(df, ['target_return_5min'])
        
        # This should fail or warn (high correlation with future)
        assert results['target_return_5min']['status'] in ['FAIL', 'WARNING']


class TestTechnicalIndicators:
    """Tests for TechnicalIndicators class."""
    
    def test_rsi_bounds(self):
        """Test RSI stays within [0, 100]."""
        df = create_mock_ohlcv(200)
        indicators = TechnicalIndicators(validate_lookahead=False)
        
        df = indicators.add_rsi(df, window=14)
        
        # RSI should be between 0 and 100
        rsi_values = df['rsi'].dropna()
        assert (rsi_values >= 0).all()
        assert (rsi_values <= 100).all()
        
        # Should have some variation
        assert rsi_values.std() > 1
    
    def test_macd_calculation(self):
        """Test MACD calculation."""
        df = create_mock_ohlcv(200)
        indicators = TechnicalIndicators(validate_lookahead=False)
        
        df = indicators.add_macd(df, fast=12, slow=26, signal=9)
        
        # Check columns created
        assert 'macd' in df.columns
        assert 'macd_signal' in df.columns
        assert 'macd_hist' in df.columns
        
        # MACD histogram should equal MACD - Signal
        macd_check = df['macd'] - df['macd_signal']
        assert np.allclose(df['macd_hist'], macd_check, equal_nan=True)
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation."""
        df = create_mock_ohlcv(200)
        indicators = TechnicalIndicators(validate_lookahead=False)
        
        df = indicators.add_bollinger_bands(df, window=20, std=2)
        
        # Check columns created
        assert 'bb_upper' in df.columns
        assert 'bb_middle' in df.columns
        assert 'bb_lower' in df.columns
        assert 'bb_width' in df.columns
        assert 'bb_position' in df.columns
        
        # Upper should be > middle > lower
        valid_rows = df.dropna(subset=['bb_upper', 'bb_middle', 'bb_lower'])
        assert (valid_rows['bb_upper'] > valid_rows['bb_middle']).all()
        assert (valid_rows['bb_middle'] > valid_rows['bb_lower']).all()
        
        # Position should be in [0, 1]
        positions = df['bb_position'].dropna()
        assert (positions >= 0).all()
        assert (positions <= 1).all()
    
    def test_indicators_no_lookahead(self):
        """Test that indicators don't have lookahead bias."""
        df = create_mock_ohlcv(1000)
        indicators = TechnicalIndicators(validate_lookahead=False)
        
        df = indicators.add_rsi(df)
        df = indicators.add_macd(df)
        
        # Check for lookahead bias
        detector = LookaheadDetector(correlation_threshold=0.7)
        results = detector.detect_lookahead(df, ['rsi', 'macd', 'macd_signal'])
        
        # All should pass (low correlation with future)
        for col in ['rsi', 'macd', 'macd_signal']:
            assert results[col]['status'] in ['PASS', 'WARNING'], \
                f"{col} failed lookahead check: {results[col]['message']}"


class TestLookaheadDetector:
    """Tests for LookaheadDetector class."""
    
    def test_detect_obvious_lookahead(self):
        """Test detection of obvious lookahead bias."""
        df = create_mock_ohlcv(1000)
        
        # Create a feature with obvious lookahead bias
        df['bad_feature'] = df['close'].shift(-5)  # DIRECTLY USES FUTURE
        
        detector = LookaheadDetector(correlation_threshold=0.7)
        results = detector.detect_lookahead(df, ['bad_feature'])
        
        # Should fail
        assert results['bad_feature']['status'] == 'FAIL'
        assert abs(results['bad_feature']['max_correlation']) > 0.9
    
    def test_detect_no_lookahead(self):
        """Test that legitimate features pass."""
        df = create_mock_ohlcv(1000)
        
        # Create a safe feature (uses past data only)
        df['safe_feature'] = df['close'].rolling(20).mean()
        
        detector = LookaheadDetector(correlation_threshold=0.7)
        results = detector.detect_lookahead(df, ['safe_feature'])
        
        # Should pass
        assert results['safe_feature']['status'] in ['PASS', 'WARNING']
    
    def test_verify_no_lookahead_raises(self):
        """Test that verify_no_lookahead raises on failure."""
        df = create_mock_ohlcv(1000)
        df['bad_feature'] = df['close'].shift(-5)
        
        detector = LookaheadDetector(correlation_threshold=0.7)
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Lookahead bias detected"):
            detector.verify_no_lookahead(df, ['bad_feature'], raise_on_fail=True)
    
    def test_verify_no_lookahead_no_raise(self):
        """Test that verify_no_lookahead doesn't raise when configured."""
        df = create_mock_ohlcv(1000)
        df['bad_feature'] = df['close'].shift(-5)
        
        detector = LookaheadDetector(correlation_threshold=0.7)
        
        # Should return False but not raise
        result = detector.verify_no_lookahead(df, ['bad_feature'], raise_on_fail=False)
        assert result is False
    
    def test_generate_report(self):
        """Test report generation."""
        df = create_mock_ohlcv(1000)
        df['good_feature'] = df['close'].rolling(20).mean()
        df['bad_feature'] = df['close'].shift(-5)
        
        detector = LookaheadDetector()
        report = detector.generate_report(df, ['good_feature', 'bad_feature'])
        
        # Report should be a string
        assert isinstance(report, str)
        
        # Report should contain summary
        assert 'LOOKAHEAD BIAS DETECTION REPORT' in report
        assert 'PASS' in report or 'FAIL' in report


class TestFeatureIntegration:
    """Integration tests for complete feature pipeline."""
    
    def test_full_feature_pipeline(self):
        """Test computing all features together."""
        df = create_mock_ohlcv(500)
        
        # Compute price features
        price_features = PriceFeatures(validate_lookahead=False)
        df = price_features.compute(df)
        
        # Compute technical indicators
        indicators = TechnicalIndicators(validate_lookahead=False)
        df = indicators.compute(df)
        
        # Should have many feature columns
        feature_cols = [c for c in df.columns if c not in 
                       ['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        assert len(feature_cols) > 20
        
        # No column should be all NaN
        for col in feature_cols:
            assert df[col].notna().sum() > 0
    
    def test_feature_health_check(self):
        """Test feature health monitoring."""
        df = create_mock_ohlcv(200)
        
        price_features = PriceFeatures(validate_lookahead=False)
        df = price_features.compute(df)
        
        # Check health metrics
        health = price_features.check_feature_health(df, ['return_5min_lag', 'volatility_20'])
        
        assert 'return_5min_lag' in health
        assert 'volatility_20' in health
        
        # Check expected keys in health metrics
        for col_health in health.values():
            assert 'nan_count' in col_health
            assert 'nan_pct' in col_health
            assert 'mean' in col_health


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
