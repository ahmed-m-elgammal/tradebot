"""
Test Infrastructure Components

Tests for configuration, logging, retry, and rate limiting.
"""


import time
from src.config import load_config, get_config
from src.utils.logger import setup_logging, get_logger
from src.utils.retry import retry_with_backoff, RetryContext
from src.utils.rate_limiter import RateLimiter
from src.utils.exceptions import DataIngestionError


def test_config():
    """Test configuration loading."""
    print("\n" + "="*60)
    print("Testing Configuration System")
    print("="*60)
    
    config = load_config('dev')
    
    print(f"Environment: {config.environment}")
    print(f"Log level: {config.logging.level}")
    print(f"Retry max attempts: {config.data.ingest.retry.max_attempts}")
    print(f"Rate limit: {config.data.ingest.rate_limit.calls_per_minute}/min")
    print(f"Bollinger window: {config.strategy.mean_reversion.bollinger_window}")
    print(f"Max position size: {config.risk.limits.max_position_size:.1%}")
    
    # Test singleton
    config2 = get_config()
    assert config is not config2  # Different objects
    assert config.environment == config2.environment  # Same values
    
    print("✅ Config test passed!")
    return config


def test_logging(config):
    """Test logging system."""
    print("\n" + "="*60)
    print("Testing Logging System")
    print("="*60)
    
    setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
        format_type='text',  # Use text for easy reading in test
        console=True
    )
    
    logger = get_logger(__name__)
    
    logger.debug("Debug message")
    logger.info("Info message with context", extra={'symbol': 'BTC/USD', 'price': 50000})
    logger.warning("Warning message")
    logger.error("Error message")
    
    print("✅ Logging test passed! (check logs/trading_bot.log)")


def test_retry():
    """Test retry logic."""
    print("\n" + "="*60)
    print("Testing Retry Logic")
    print("="*60)
    
    # Test successful retry
    attempt_count = [0]
    
    @retry_with_backoff(max_attempts=3, base_delay=0.1, max_delay=1.0)
    def flaky_function():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise ConnectionError(f"Attempt {attempt_count[0]} failed")
        return "Success on attempt 3"
    
    result = flaky_function()
    print(f"Result: {result}")
    print(f"Total attempts: {attempt_count[0]}")
    assert attempt_count[0] == 3
    
    # Test max retries exhausted
    @retry_with_backoff(max_attempts=2, base_delay=0.1)
    def always_fails():
        raise ValueError("Always fails")
    
    try:
        always_fails()
        assert False, "Should have raised exception"
    except ValueError:
        print("✅ Correctly raised exception after max retries")
    
    print("✅ Retry test passed!")


def test_rate_limiter():
    """Test rate limiter."""
    print("\n" + "="*60)
    print("Testing Rate Limiter")
    print("="*60)
    
    # Create limiter: 6 calls per minute (1 per 10 seconds)
    limiter = RateLimiter(calls_per_minute=6, burst_size=3)
    
    # Burst should succeed immediately
    start = time.time()
    for i in range(3):
        limiter.acquire()
        print(f"Call {i+1} at {time.time() - start:.2f}s")
    
    print(f"\nBurst of 3 calls completed in {time.time() - start:.2f}s")
    
    # Next call should be delayed
    print("\nNext call should wait ~10s...")
    start_wait = time.time()
    limiter.acquire()
    wait_time = time.time() - start_wait
    print(f"Call 4 waited {wait_time:.2f}s")
    
    # Get stats
    stats = limiter.get_stats()
    print(f"\nRate limiter stats: {stats}")
    
    print("✅ Rate limiter test passed!")


def test_integration():
    """Test components working together."""
    print("\n" + "="*60)
    print("Testing Integration")
    print("="*60)
    
    logger = get_logger(__name__)
    config = get_config()
    
    limiter = RateLimiter(
        calls_per_minute=config.data.ingest.rate_limit.calls_per_minute,
        burst_size=config.data.ingest.rate_limit.burst_size
    )
    
    @retry_with_backoff(
        max_attempts=config.data.ingest.retry.max_attempts,
        base_delay=config.data.ingest.retry.base_delay,
        exceptions=(ConnectionError, DataIngestionError)
    )
    def fetch_data_with_rate_limit():
        limiter.acquire()
        logger.info("Fetching data", extra={'endpoint': '/api/data'})
        return {'data': [1, 2, 3]}
    
    result = fetch_data_with_rate_limit()
    print(f"Fetched: {result}")
    
    print("✅ Integration test passed!")


if __name__ == '__main__':
    print("\n" + "="*70)
    print(" INFRASTRUCTURE TEST SUITE")
    print("="*70)
    
    try:
        config = test_config()
        test_logging(config)
        test_retry()
        test_rate_limiter()
        test_integration()
        
        print("\n" + "="*70)
        print(" ✅ ALL TESTS PASSED!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
