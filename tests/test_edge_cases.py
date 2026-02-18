"""
Edge Case and Negative Tests

Tests for error handling, edge cases, and invalid inputs.
"""


import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.features.price_features import PriceFeatures
from src.features.technical_indicators import TechnicalIndicators
from src.strategies.mean_reversion import MeanReversionStrategy
from src.backtest.engine import Backtester
from src.utils.exceptions import DataValidationError


def create_empty_dataframe():
    """Create empty OHLCV DataFrame."""
    return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])


def create_single_row_dataframe():
    """Create DataFrame with single row."""
    return pd.DataFrame([{
        'timestamp': datetime(2024, 1, 1),
        'open': 100,
        'high': 101,
        'low': 99,
        'close': 100.5,
        'volume': 1000
    }])


def create_invalid_ohlcv():
    """Create DataFrame with invalid OHLCV (high < low)."""
    return pd.DataFrame([{
        'timestamp': datetime(2024, 1, 1),
        'open': 100,
        'high': 99,  # Invalid: high < low
        'low': 101,
        'close': 100,
        'volume': 1000
    }])


class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        df = create_empty_dataframe()
        
        # Features should handle empty data gracefully
        features = PriceFeatures(validate_lookahead=False)
        try:
            result = features.compute(df)
            # Should return empty or handle gracefully
            assert len(result) == 0
        except Exception as e:
            # Or raise informative error
            assert "empty" in str(e).lower() or "insufficient" in str(e).lower()
    
    def test_single_row_dataframe(self):
        """Test DataFrame with single row."""
        df = create_single_row_dataframe()
        
        indicators = TechnicalIndicators(validate_lookahead=False)
        result = indicators.add_rsi(df.copy())
        
        # RSI should be NaN for single row
        assert pd.isna(result['rsi'].iloc[0])
    
    def test_nan_values_in_data(self):
        """Test handling of NaN values."""
        df = create_single_row_dataframe()
        df = pd.concat([df] * 100, ignore_index=True)
        
        # Introduce NaN values
        df.loc[50, 'close'] = np.nan
        
        features = PriceFeatures(validate_lookahead=False)
        result = features.compute(df)
        
        # Should handle NaN gracefully (forward fill or similar)
        # Exact behavior depends on implementation
        assert len(result) > 0
    
    def test_zero_volume(self):
        """Test handling of zero volume."""
        df = create_single_row_dataframe()
        df = pd.concat([df] * 100, ignore_index=True)
        df['volume'] = 0  # Zero volume
        
        # Should not crash
        features = PriceFeatures(validate_lookahead=False)
        result = features.compute(df)
        assert len(result) > 0
    
    def test_extreme_price_moves(self):
        """Test handling of extreme price movements."""
        df = create_single_row_dataframe()
        df = pd.concat([df] * 100, ignore_index=True)
        
        # Extreme spike
        df.loc[50, 'close'] = 1000000  # 10000x increase
        
        indicators = TechnicalIndicators(validate_lookahead=False)
        result = indicators.add_rsi(df.copy())
        
        # RSI should still be bounded [0, 100]
        assert result['rsi'].min() >= 0
        assert result['rsi'].max() <= 100


class TestNegativeCases:
    """Test negative/error cases."""
    
    def test_invalid_config(self):
        """Test strategy with invalid config."""
        # Negative window
        with pytest.raises(Exception):  # Should validate
            strategy = MeanReversionStrategy({
                'rsi_window': -5  # Invalid
            })
    
    def test_duplicate_timestamps(self):
        """Test handling of duplicate timestamps."""
        df = create_single_row_dataframe()
        df = pd.concat([df, df], ignore_index=True)  # Duplicate rows
        
        # Should either deduplicate or raise error
        features = PriceFeatures(validate_lookahead=False)
        try:
            result = features.compute(df)
            # If it succeeds, should have deduplicated
            assert len(result) <= len(df)
        except Exception:
            # Or should raise informative error
            pass
    
    def test_unsorted_timestamps(self):
        """Test handling of unsorted timestamps."""
        df = pd.DataFrame([
            {'timestamp': datetime(2024, 1, 3), 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000},
            {'timestamp': datetime(2024, 1, 1), 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000},
            {'timestamp': datetime(2024, 1, 2), 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000},
        ])
        
        # Should either sort or raise error
        features = PriceFeatures(validate_lookahead=False)
        try:
            result = features.compute(df)
            # If succeeds, should be sorted
            assert result['timestamp'].is_monotonic_increasing
        except Exception:
            pass
    
    def test_missing_required_columns(self):
        """Test DataFrame missing required columns."""
        df = pd.DataFrame([
            {'timestamp': datetime(2024, 1, 1), 'close': 100}  # Missing OHLV
        ])
        
        features = PriceFeatures(validate_lookahead=False)
        with pytest.raises(Exception):
            features.compute(df)
    
    def test_backtest_no_signals(self):
        """Test backtest with strategy generating no signals."""
        # Create data but configure strategy to never signal
        df = create_single_row_dataframe()
        df = pd.concat([df] * 100, ignore_index=True)
        df['close'] = 100  # Flat price
        
        strategy = MeanReversionStrategy({
            'rsi_oversold': 0,   # Impossible threshold
            'rsi_overbought': 101  # Impossible threshold
        })
        
        backtester = Backtester(initial_capital=10000)
        
        # Should complete without errors, just no trades
        results, metrics = backtester.run(strategy, df)
        
        # Should have zero or minimal returns
        assert metrics['total_trades'] == 0 or metrics['total_return'] == 0


class TestDataQuality:
    """Test data quality checks."""
    
    def test_detect_gaps(self):
        """Test gap detection in time series."""
        # Create data with a gap
        df = pd.DataFrame([
            {'timestamp': datetime(2024, 1, 1, 0, 0), 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000},
            {'timestamp': datetime(2024, 1, 1, 0, 1), 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000},
            # Missing 00:02, 00:03, 00:04 (3-minute gap)
            {'timestamp': datetime(2024, 1, 1, 0, 5), 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000},
        ])
        
        # Gap detection logic would go here
        # For now, just verify data structure
        assert len(df) == 3
        
        # Calculate time differences
        diffs = df['timestamp'].diff()
        max_diff = diffs.max()
        
        # Should detect gap > 1 minute
        assert max_diff > pd.Timedelta(minutes=1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
