"""
Unit Tests for Utility Modules

Tests for retry logic, rate limiter, and logger.
"""


import pytest
import time
from src.utils.retry import retry_with_backoff, RetryContext
from src.utils.rate_limiter import RateLimiter
from src.utils.exceptions import DataIngestionError


class TestRetry:
    """Test retry logic."""
    
    def test_successful_retry(self):
        """Test function succeeds after retries."""
        attempts = [0]
        
        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def flaky_func():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ConnectionError("Failed")
            return "Success"
        
        result = flaky_func()
        assert result == "Success"
        assert attempts[0] == 3
    
    def test_max_retries_exhausted(self):
        """Test exception raised after max retries."""
        @retry_with_backoff(max_attempts=2, base_delay=0.01)
        def always_fails():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_fails()
    
    def test_retry_context(self):
        """Test RetryContext class."""
        retry_ctx = RetryContext(max_attempts=2, base_delay=0.01)
        
        attempts = [0]
        def func():
            attempts[0] += 1
            if attempts[0] < 2:
                raise ConnectionError("Failed")
            return "Success"
        
        result = retry_ctx.execute(func)
        assert result == "Success"
        assert attempts[0] == 2
    
    def test_specific_exceptions_only(self):
        """Test only specific exceptions are retried."""
        @retry_with_backoff(max_attempts=3, base_delay=0.01, exceptions=(ConnectionError,))
        def raises_wrong_exception():
            raise ValueError("Not retryable")
        
        # Should raise immediately without retries
        with pytest.raises(ValueError):
            raises_wrong_exception()


class TestRateLimiter:
    """Test rate limiter."""
    
    def test_burst_allowed(self):
        """Test burst calls succeed immediately."""
        limiter = RateLimiter(calls_per_minute=60, burst_size=3)
        
        start = time.time()
        for _ in range(3):
            limiter.acquire()
        elapsed = time.time() - start
        
        # Should complete almost instantly
        assert elapsed < 0.5
    
    def test_rate_limiting_delays(self):
        """Test rate limiting delays calls."""
        limiter = RateLimiter(calls_per_minute=60, burst_size=1)
        
        limiter.acquire()  # First call (uses burst)
        
        start = time.time()
        limiter.acquire()  # Second call (should wait ~1 second)
        elapsed = time.time() - start
        
        # Should wait approximately 1 second
        assert 0.9 < elapsed < 1.5
    
    def test_non_blocking_acquire(self):
        """Test non-blocking acquire returns False when no tokens."""
        limiter = RateLimiter(calls_per_minute=60, burst_size=1)
        
        # First call succeeds
        assert limiter.acquire(blocking=False) == True
        
        # Second call fails (no tokens)
        assert limiter.acquire(blocking=False) == False
    
    def test_reset(self):
        """Test reset refills tokens."""
        limiter = RateLimiter(calls_per_minute=60, burst_size=2)
        
        limiter.acquire()
        limiter.acquire()
        
        # Should have no tokens
        assert limiter.acquire(blocking=False) == False
        
        # Reset
        limiter.reset()
        
        # Should have tokens again
        assert limiter.acquire(blocking=False) == True
    
    def test_stats(self):
        """Test statistics tracking."""
        limiter = RateLimiter(calls_per_minute=60, burst_size=5)
        
        for _ in range(3):
            limiter.acquire()
        
        stats = limiter.get_stats()
        assert stats['calls_per_minute_limit'] == 60
        assert stats['current_rate'] == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
