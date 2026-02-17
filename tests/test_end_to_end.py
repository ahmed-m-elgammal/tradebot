"""
End-to-End Integration Test

Tests the complete trading system from data ingestion through backtesting.
"""

import sys
sys.path.insert(0, 'c:\\Users\\A-Dev\\Desktop\\Trading Bot')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import all modules
from src.features.price_features import PriceFeatures
from src.features.technical_indicators import TechnicalIndicators
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.position_sizer import PositionSizer
from src.risk.limits import RiskLimits, Order, Position
from src.backtest.engine import Backtester


def create_test_data(n=500):
    """Create realistic test data."""
    np.random.seed(42)
    timestamps = [datetime(2024, 1, 1) + timedelta(minutes=i) for i in range(n)]
    
    # Generate trending + mean-reverting price series
    trend = np.linspace(0, 0.1, n)
    noise = np.random.normal(0, 0.01, n)
    returns = trend / n + noise
    prices = 100 * np.cumprod(1 + returns)
    
    data = []
    for i, (ts, close) in enumerate(zip(timestamps, prices)):
        vol_mult = np.random.uniform(0.98, 1.02)
        data.append({
            'timestamp': ts,
            'open': close * 0.999,
            'high': close * vol_mult,
            'low': close * (2 - vol_mult),
            'close': close,
            'volume': np.random.uniform(500000, 2000000)
        })
    
    return pd.DataFrame(data)


def test_complete_pipeline():
    """Test complete trading pipeline."""
    print("=" * 60)
    print("COMPLETE TRADING SYSTEM TEST")
    print("=" * 60)
    
    # 1. Create test data
    print("\n1. Creating test data...")
    df = create_test_data(500)
    print(f"   ✓ Created {len(df)} bars of OHLCV data")
    
    # 2. Feature engineering
    print("\n2. Computing features...")
    price_features = PriceFeatures(validate_lookahead=False)
    df = price_features.compute(df)
    
    indicators = TechnicalIndicators(validate_lookahead=False)
    df = indicators.compute(df)
    print(f"   ✓ Computed {len([c for c in df.columns if c not in ['timestamp', 'open', 'high', 'low', 'close', 'volume']])} features")
    
    # 3. Strategy signal generation
    print("\n3. Generating trading signals...")
    strategy = MeanReversionStrategy({
        'bollinger_window': 20,
        'rsi_window': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70
    })
    df = strategy.generate_signals(df)
    
    stats = strategy.get_statistics(df)
    print(f"   ✓ Generated signals:")
    print(f"     - Buy signals: {stats['buy_signals']} ({stats['buy_pct']:.1%})")
    print(f"     - Sell signals: {stats['sell_signals']} ({stats['sell_pct']:.1%})")
    print(f"     - Signal changes: {stats['signal_changes']}")
    
    # 4. Position sizing
    print("\n4. Testing position sizer...")
    sizer = PositionSizer()
    
    # Test Kelly
    kelly_size = sizer.kelly_sizing(
        win_rate=0.55,
        avg_win=0.02,
        avg_loss=0.015,
        equity=10000,
        safety_factor=0.5
    )
    print(f"   ✓ Kelly position size: ${kelly_size:.2f}")
    
    # Test fixed fractional
    fixed_size = sizer.fixed_fractional(equity=10000, risk_per_trade=0.01)
    print(f"   ✓ Fixed fractional (1%): ${fixed_size:.2f}")
    
    # 5. Risk management
    print("\n5. Testing risk limits...")
    risk_limits = RiskLimits({
        'max_position_size': 0.05,
        'max_portfolio_heat': 0.10,
        'max_drawdown': 0.15,
        'daily_loss_limit': 0.03
    })
    
    # Test order approval
    test_order = Order(symbol='TEST', quantity=10, price=100, stop_loss=95)
    approved, reason = risk_limits.check_order(test_order, current_equity=10000, open_positions=[])
    print(f"   ✓ Order check: {approved} - {reason}")
    
    # Test with too large position
    large_order = Order(symbol='TEST', quantity=100, price=100)
    approved, reason = risk_limits.check_order(large_order, current_equity=10000, open_positions=[])
    print(f"   ✓ Large order check: {approved} - {reason}")
    
    # 6. Backtesting
    print("\n6. Running backtest...")
    backtester = Backtester(
        initial_capital=10000,
        commission_pct=0.001,
        slippage_pct=0.002
    )
    
    results, metrics = backtester.run(strategy, df)
    
    print(f"\n   ✓ Backtest Results:")
    print(f"     - Total Return: {metrics['total_return']:.2%}")
    print(f"     - Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"     - Sortino Ratio: {metrics['sortino_ratio']:.2f}")
    print(f"     - Max Drawdown: {metrics['max_drawdown']:.2%}")
    print(f"     - Win Rate: {metrics['win_rate']:.1%}")
    print(f"     - Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"     - Total Trades: {metrics['total_trades']}")
    print(f"     - Calmar Ratio: {metrics['calmar_ratio']:.2f}")
    
    # 7. Verify results are reasonable
    print("\n7. Validating results...")
    
    assert 'equity' in results.columns, "Missing equity column"
    assert len(results) == len(df), "Results length mismatch"
    assert results['equity'].iloc[0] == backtester.initial_capital, "Initial equity incorrect"
    assert metrics['total_trades'] > 0, "No trades executed"
    assert -1 <= metrics['max_drawdown'] <= 0, "Invalid drawdown"
    assert 0 <= metrics['win_rate'] <= 1, "Invalid win rate"
    
    print("   ✓ All validations passed!")
    
    # 8. Sample trades
    print("\n8. Sample trades (first 5 signal changes):")
    signal_changes = results[results['signal'].diff() != 0].head(5)
    for idx, row in signal_changes.iterrows():
        if row['signal'] == 1:
            signal_type = "BUY"
        elif row['signal'] == -1:
            signal_type = "SELL"
        else:
            signal_type = "FLAT"
        
        print(f"   {row['timestamp']}: {signal_type} @ ${row['close']:.2f} "
              f"(RSI: {row.get('rsi', 0):.1f})")
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE SYSTEM TEST PASSED!")
    print("=" * 60)
    
    return results, metrics


if __name__ == '__main__':
    try:
        results, metrics = test_complete_pipeline()
        print("\n✅ All tests completed successfully!")
        print(f"\nFinal Equity: ${results['equity'].iloc[-1]:.2f}")
        print(f"Total Return: {metrics['total_return']:.2%}")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
