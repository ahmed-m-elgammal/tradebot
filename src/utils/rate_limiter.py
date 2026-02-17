"""
Rate Limiter

Token bucket rate limiter for API calls.
"""

import time
from typing import Optional
from collections import deque
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.
    
    Allows bursts up to burst_size, then enforces calls_per_minute rate.
    
    Thread-safe implementation.
    
    Example:
        limiter = RateLimiter(calls_per_minute=60, burst_size=10)
        
        limiter.acquire()  # May block if rate limit exceeded
        response = api.call()
    """
    
    def __init__(self, calls_per_minute: int, burst_size: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_minute: Maximum calls per minute
            burst_size: Maximum burst allowance (default: same as calls_per_minute)
        """
        if calls_per_minute <= 0:
            raise ValueError("calls_per_minute must be positive")
        
        self.calls_per_minute = calls_per_minute
        self.burst_size = burst_size if burst_size is not None else calls_per_minute
        self.tokens = float(self.burst_size)
        self.last_update = time.time()
        self.lock = Lock()
        self.call_times = deque(maxlen=calls_per_minute)
        
        logger.debug(
            "Rate limiter initialized",
            extra={
                'calls_per_minute': calls_per_minute,
                'burst_size': self.burst_size
            }
        )
    
    def acquire(self, blocking: bool = True) -> bool:
        """
        Acquire permission to make a call.
        
        Args:
            blocking: If True, block until token available. If False, return immediately.
            
        Returns:
            True if acquired, False if not available (only when blocking=False)
        """
        with self.lock:
            now = time.time()
            
            # Refill tokens based on time passed
            time_passed = now - self.last_update
            new_tokens = time_passed * self.calls_per_minute / 60.0
            self.tokens = min(self.burst_size, self.tokens + new_tokens)
            self.last_update = now
            
            # Check if we have tokens
            if self.tokens >= 1:
                self.tokens -= 1
                self.call_times.append(now)
                return True
            
            # No tokens available
            if not blocking:
                return False
            
            # Calculate wait time
            wait_time = (1 - self.tokens) * 60.0 / self.calls_per_minute
            
            logger.debug(
                f"Rate limit hit, waiting {wait_time:.2f}s",
                extra={'wait_time': wait_time, 'tokens': self.tokens}
            )
        
        # Sleep outside the lock
        time.sleep(wait_time)
        
        # Try again after sleeping
        with self.lock:
            self.tokens = 0  # Already waited for full second refill
            self.last_update = time.time()
            self.call_times.append(self.last_update)
            return True
    
    def get_stats(self) -> dict:
        """
        Get current rate limiter statistics.
        
        Returns:
            Dictionary with stats
        """
        with self.lock:
            now = time.time()
            
            # Calculate current rate (calls in last 60 seconds)
            recent_calls = [t for t in self.call_times if now - t <= 60]
            current_rate = len(recent_calls)
            
            return {
                'tokens': self.tokens,
                'calls_per_minute_limit': self.calls_per_minute,
                'current_rate': current_rate,
                'utilization': current_rate / self.calls_per_minute if self.calls_per_minute > 0 else 0
            }
    
    def reset(self):
        """Reset the rate limiter (refill all tokens)."""
        with self.lock:
            self.tokens = float(self.burst_size)
            self.last_update = time.time()
            self.call_times.clear()
            logger.info("Rate limiter reset")
