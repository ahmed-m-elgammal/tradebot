"""
Retry Logic with Exponential Backoff

Automatic retry for transient failures.
"""

import time
import random
from typing import Callable, Type, Tuple, TypeVar, Optional
import logging
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        exceptions: Exception types to catch and retry
        on_retry: Optional callback called before each retry
        
    Returns:
        Decorated function
        
    Example:
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        def fetch_data():
            return api.get_data()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"Max retries ({max_attempts}) exhausted for {func.__name__}",
                            extra={
                                'function': func.__name__,
                                'attempt': attempt,
                                'error': str(e),
                                'error_type': type(e).__name__
                            }
                        )
                        raise
                    
                    # Calculate backoff with jitter
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    sleep_time = delay + jitter
                    
                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for {func.__name__} after {sleep_time:.2f}s",
                        extra={
                            'function': func.__name__,
                            'attempt': attempt,
                            'max_attempts': max_attempts,
                            'delay': sleep_time,
                            'error': str(e),
                            'error_type': type(e).__name__
                        }
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt, e)
                    
                    time.sleep(sleep_time)
            
            # This should never be reached, but makes type checker happy
            raise RuntimeError("Retry logic error")
        
        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for retry logic.
    
    Useful when you can't use a decorator.
    
    Example:
        retry_ctx = RetryContext(max_attempts=3)
        result = retry_ctx.execute(lambda: api.get_data())
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exceptions = exceptions
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        for attempt in range(1, self.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except self.exceptions as e:
                if attempt == self.max_attempts:
                    logger.error(
                        f"Max retries ({self.max_attempts}) exhausted",
                        extra={'attempt': attempt, 'error': str(e)}
                    )
                    raise
                
                delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                jitter = random.uniform(0, delay * 0.1)
                sleep_time = delay + jitter
                
                logger.warning(
                    f"Retry {attempt}/{self.max_attempts} after {sleep_time:.2f}s",
                    extra={'attempt': attempt, 'delay': sleep_time, 'error': str(e)}
                )
                
                time.sleep(sleep_time)
        
        raise RuntimeError("Retry logic error")
