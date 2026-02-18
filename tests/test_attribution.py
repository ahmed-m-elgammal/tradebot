"""
Unit Tests for Attribution Module

Tests for P&L breakdown and attribution analysis.
"""


import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.backtest.attribution import AttributionAnalyzer, Trade


def create_sample_trades():
    """Create sample trades for testing."""
    base_time = datetime(2024, 1, 1)
    
    trades = [
        # Winning long trade
        Trade(
            timestamp=base_time,
            symbol='BTC/USD',
            side='BUY',
            quantity=1.0,
            entry_price=50000,
            exit_price=51000,
            exit_timestamp=base_time + timedelta(hours=1),
            commission=50,
            slippage=100
        ),
        # Losing short trade
        Trade(
            timestamp=base_time + timedelta(hours=2),
            symbol='ETH/USD',
            side='SELL',
            quantity=10.0,
            entry_price=3000,
            exit_price=3100,
            exit_timestamp=base_time + timedelta(hours=3),
            commission=30,
            slippage=50
        ),
        # Winning long trade (same symbol)
        Trade(
            timestamp=base_time + timedelta(days=1),
            symbol='BTC/USD',
            side='BUY',
            quantity=0.5,
            entry_price=51000,
            exit_price=52000,
            exit_timestamp=base_time + timedelta(days=1, hours=2),
            commission=25,
            slippage=50
        ),
    ]
    
    return trades


class TestTrade:
    """Test Trade dataclass."""
    
    def test_trade_pnl_long(self):
        """Test P&L calculation for long trade."""
        trade = Trade(
            timestamp=datetime.now(),
            symbol='BTC/USD',
            side='BUY',
            quantity=1.0,
            entry_price=50000,
            exit_price=51000,
            exit_timestamp=datetime.now(),
            commission=50,
            slippage=100
        )
        
        # Gross: 1 * (51000 - 50000) = 1000
        # Net: 1000 - 50 - 100 = 850
        assert trade.pnl == 850
    
    def test_trade_pnl_short(self):
        """Test P&L calculation for short trade."""
        trade = Trade(
            timestamp=datetime.now(),
            symbol='BTC/USD',
            side='SELL',
            quantity=1.0,
            entry_price=50000,
            exit_price=49000,
            exit_timestamp=datetime.now(),
            commission=50,
            slippage=100
        )
        
        # Gross: 1 * (50000 - 49000) = 1000
        # Net: 1000 - 50 - 100 = 850
        assert trade.pnl == 850
    
    def test_trade_return_pct(self):
        """Test return percentage calculation."""
        trade = Trade(
            timestamp=datetime.now(),
            symbol='BTC/USD',
            side='BUY',
            quantity=1.0,
            entry_price=50000,
            exit_price=51000,
            exit_timestamp=datetime.now(),
            commission=50,
            slippage=100
        )
        
        # 850 / 50000 = 0.017 = 1.7%
        assert abs(trade.return_pct - 0.017) < 0.001
    
    def test_open_trade(self):
        """Test open (unclosed) trade."""
        trade = Trade(
            timestamp=datetime.now(),
            symbol='BTC/USD',
            side='BUY',
            quantity=1.0,
            entry_price=50000
        )
        
        assert not trade.is_closed
        assert trade.pnl == 0
        assert trade.holding_period is None


class TestAttributionAnalyzer:
    """Test AttributionAnalyzer."""
    
    def test_analyze_by_symbol(self):
        """Test P&L analysis by symbol."""
        analyzer = AttributionAnalyzer()
        trades = create_sample_trades()
        
        for trade in trades:
            analyzer.add_trade(trade)
        
        by_symbol = analyzer.analyze_by_symbol()
        
        # Should have 2 symbols
        assert len(by_symbol) == 2
        
        # BTC should have 2 trades
        btc_row = by_symbol[by_symbol['symbol'] == 'BTC/USD'].iloc[0]
        assert btc_row['num_trades'] == 2
    
    def test_analyze_by_direction(self):
        """Test P&L analysis by direction."""
        analyzer = AttributionAnalyzer()
        trades = create_sample_trades()
        
        for trade in trades:
            analyzer.add_trade(trade)
        
        by_direction = analyzer.analyze_by_direction()
        
        # Should have stats for long and short
        assert 'long' in by_direction
        assert 'short' in by_direction
        assert 'total' in by_direction
        
        # 2 longs, 1 short
        assert by_direction['long']['num_trades'] == 2
        assert by_direction['short']['num_trades'] == 1
        assert by_direction['total']['num_trades'] == 3
    
    def test_analyze_costs(self):
        """Test cost analysis."""
        analyzer = AttributionAnalyzer()
        trades = create_sample_trades()
        
        for trade in trades:
            analyzer.add_trade(trade)
        
        costs = analyzer.analyze_costs()
        
        # Total commission: 50 + 30 + 25 = 105
        assert costs['total_commission'] == 105
        
        # Total slippage: 100 + 50 + 50 = 200
        assert costs['total_slippage'] == 200
        
        # Total costs
        assert costs['total_costs'] == 305
        
        # Cost ratio should be > 0
        assert costs['cost_ratio'] > 0
    
    def test_get_summary(self):
        """Test comprehensive summary."""
        analyzer = AttributionAnalyzer()
        trades = create_sample_trades()
        
        for trade in trades:
            analyzer.add_trade(trade)
        
        summary = analyzer.get_summary()
        
        assert summary['num_trades'] == 3
        assert summary['num_open'] == 0
        assert 'total_pnl' in summary
        assert 'by_direction' in summary
        assert 'by_costs' in summary
    
    def test_generate_report(self):
        """Test report generation."""
        analyzer = AttributionAnalyzer()
        trades = create_sample_trades()
        
        for trade in trades:
            analyzer.add_trade(trade)
        
        report = analyzer.generate_report()
        
        # Check report contains key sections
        assert 'P&L ATTRIBUTION REPORT' in report
        assert 'BY DIRECTION' in report
        assert 'COST BREAKDOWN' in report
        assert 'TOP SYMBOLS' in report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
