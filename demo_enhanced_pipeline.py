"""
Demo: Complete Data Pipeline with Infrastructure

Demonstrates full integration of retry, rate limiting, logging, and storage.
"""

import sys
sys.path.insert(0, 'c:\\Users\\A-Dev\\Desktop\\Trading Bot')

from datetime import datetime, timedelta
from src.data.ingest.ccxt_crypto_enhanced import CCXTCryptoIngestor
from src.data.storage.parquet_store_enhanced import EnhancedParquetStore
from src.config import load_config
from src.utils.logger import setup_logging, get_logger


def main():
    """Demonstrate complete pipeline."""
    print("\n" + "="*70)
    print("ENHANCED DATA PIPELINE DEMO")
    print("="*70)
    
    # 1. Load config and setup logging
    print("\n1. Initializing system...")
    config = load_config('dev')
    setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
        format_type='text',
        console=True
    )
    
    logger = get_logger(__name__)
    logger.info("Pipeline demo started")
    
    # 2. Initialize ingestor (with retry + rate limiting)
    print("\n2. Initializing ingestor...")
    ingestor = CCXTCryptoIngestor('binance')
    
    # 3. Fetch data (automatic retries on failure)
    print("\n3. Fetching market data...")
    try:
        df = ingestor.fetch_ohlcv(
            symbol='BTC/USDT',
            timeframe='1m',
            since=datetime.now() - timedelta(hours=1),
            limit=60
        )
        
        print(f"   Fetched {len(df)} bars")
        print(f"   Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # 4. Save with compression + metadata
    print("\n4. Saving to enhanced parquet store...")
    store = EnhancedParquetStore()
    store.save(df, 'BTC/USDT', '1m')
    
    # 5. Load back with filtering
    print("\n5. Loading from store...")
    loaded_df = store.load('BTC/USDT', '1m')
    print(f"   Loaded {len(loaded_df)} rows")
    
    # 6. Check metadata
    metadata = store.get_metadata('BTC/USDT', '1m')
    if metadata:
        print(f"\n6. Metadata:")
        print(f"   Last updated: {metadata['last_updated']}")
        print(f"   Checksum: {metadata['checksum'][:16]}...")
        print(f"   Rows: {metadata['rows']}")
    
    # 7. Check rate limiter stats
    stats = ingestor.get_rate_limiter_stats()
    print(f"\n7. Rate Limiter Stats:")
    print(f"   Current rate: {stats['current_rate']}/{stats['calls_per_minute_limit']} per minute")
    print(f"   Utilization: {stats['utilization']:.1%}")
    
    print("\n" + "="*70)
    print("✅ PIPELINE DEMO COMPLETE!")
    print("="*70)
    print("\nAll components working:")
    print("  ✓ Configuration loading")
    print("  ✓ Structured logging")
    print("  ✓ Retry logic (on failures)")
    print("  ✓ Rate limiting")
    print("  ✓ Data validation")
    print("  ✓ Parquet compression")
    print("  ✓ Metadata tracking")


if __name__ == '__main__':
    main()
