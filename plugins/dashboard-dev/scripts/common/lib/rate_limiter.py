"""
Global rate limiter for DevRev API requests using token bucket algorithm.

Provides:
- Token bucket algorithm for smooth request distribution
- Semaphore for concurrency control
- Dynamic throttling based on API headers
- Exponential backoff on 429 errors
"""

import asyncio
import time
from typing import Optional
from contextlib import asynccontextmanager


class RateLimiterContext:
    """Context manager for rate limiter token acquisition."""

    def __init__(self, limiter: 'RateLimiter'):
        self.limiter = limiter

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.limiter.semaphore.release()


class RateLimiter:
    """
    Global rate limiter tracking API quota across all concurrent operations.

    Features:
    - Token bucket algorithm for smooth request distribution
    - Semaphore for concurrency control
    - Header-based dynamic adjustment
    - Exponential backoff on 429 errors

    Args:
        max_requests: Maximum requests allowed per window (default: 150)
        window_seconds: Time window in seconds (default: 60)

    Example:
        >>> limiter = RateLimiter(max_requests=150, window_seconds=60)
        >>> async with limiter.acquire():
        >>>     response = await client.make_request(...)
        >>>     limiter.update_from_headers(response.headers)
    """

    def __init__(self, max_requests: int = 150, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Max requests per window (default: 150, safe for 1000/5min limit)
            window_seconds: Window duration in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        # Semaphore controls max concurrent requests
        # Start conservative: max_requests // 10
        initial_concurrent = max(3, min(max_requests // 10, 20))
        self.semaphore = asyncio.Semaphore(initial_concurrent)

        # Token bucket state
        self.tokens = float(max_requests)
        self.last_refill = time.time()
        self.tokens_lock = asyncio.Lock()

        # Rate limit tracking from API headers
        self.limit_remaining: Optional[int] = None
        self.limit_reset: Optional[int] = None
        self.limit_total: Optional[int] = None

        # Statistics
        self.total_requests = 0
        self.total_429s = 0
        self.total_throttles = 0

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire permission to make API request.

        Manages semaphore and token bucket automatically.

        Usage:
            async with limiter.acquire():
                # Make API request here
                pass
        """
        await self.semaphore.acquire()
        try:
            await self._wait_for_token()
            self.total_requests += 1
            yield
        finally:
            self.semaphore.release()

    async def _wait_for_token(self):
        """Wait until a token is available from the bucket."""
        while True:
            async with self.tokens_lock:
                await self._refill_tokens()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return

                # Calculate wait time based on refill rate
                wait_time = (1.0 - self.tokens) * (self.window_seconds / self.max_requests)

            # Wait outside the lock
            await asyncio.sleep(max(0.01, wait_time))

    async def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Calculate tokens to add based on elapsed time
        refill_rate = self.max_requests / self.window_seconds
        new_tokens = elapsed * refill_rate

        # Add tokens, capped at max_requests
        self.tokens = min(self.max_requests, self.tokens + new_tokens)
        self.last_refill = now

    def update_from_headers(self, headers: dict):
        """
        Update rate limit state from response headers.

        Dynamically throttles if approaching API limits.

        Args:
            headers: HTTP response headers (dict or case-insensitive)

        Expected headers:
            - X-Ratelimit-Limit: Total rate limit units
            - X-Ratelimit-Remaining: Remaining units in window
            - X-Ratelimit-Reset: Unix timestamp when window resets
        """
        # Handle both dict and case-insensitive header objects
        def get_header(key: str) -> Optional[str]:
            # Try exact case
            if key in headers:
                return headers[key]
            # Try case-insensitive
            for h_key, h_val in headers.items():
                if h_key.lower() == key.lower():
                    return h_val
            return None

        remaining_str = get_header('X-Ratelimit-Remaining')
        limit_str = get_header('X-Ratelimit-Limit')
        reset_str = get_header('X-Ratelimit-Reset')

        if remaining_str is not None:
            try:
                self.limit_remaining = int(remaining_str)
            except (ValueError, TypeError):
                pass

        if limit_str is not None:
            try:
                self.limit_total = int(limit_str)
            except (ValueError, TypeError):
                pass

        if reset_str is not None:
            try:
                self.limit_reset = int(reset_str)
            except (ValueError, TypeError):
                pass

        # Dynamic throttling if approaching limit
        if self.limit_remaining is not None and self.limit_remaining < 50:
            # Reduce concurrency when low on quota
            new_concurrency = max(2, self.limit_remaining // 10)
            if hasattr(self.semaphore, '_value') and self.semaphore._value > new_concurrency:
                self.semaphore._value = new_concurrency
                self.total_throttles += 1

    async def handle_429(self, response, attempt: int) -> int:
        """
        Handle 429 error with exponential backoff.

        Args:
            response: HTTP response object with headers
            attempt: Current retry attempt number (0-indexed)

        Returns:
            Delay in seconds to wait before retry
        """
        self.total_429s += 1

        # Extract retry-after from header
        retry_after = None
        if hasattr(response, 'headers'):
            # Try both common header names
            retry_after = response.headers.get('Retry-After') or response.headers.get('retry-after')

        if retry_after:
            try:
                delay = int(retry_after)
            except (ValueError, TypeError):
                # Fallback to exponential backoff
                delay = min(2 ** attempt, 60)
        else:
            # Exponential backoff: 1s, 2s, 4s, 8s, ..., max 60s
            delay = min(2 ** attempt, 60)

        # Reduce concurrency temporarily to avoid more 429s
        if hasattr(self.semaphore, '_value') and self.semaphore._value > 1:
            self.semaphore._value = max(1, self.semaphore._value // 2)
            self.total_throttles += 1

        return delay

    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with:
            - total_requests: Total requests made
            - total_429s: Number of 429 errors encountered
            - total_throttles: Number of times concurrency was reduced
            - current_concurrency: Current semaphore value
            - limit_remaining: Last known remaining quota
        """
        return {
            'total_requests': self.total_requests,
            'total_429s': self.total_429s,
            'total_throttles': self.total_throttles,
            'current_concurrency': getattr(self.semaphore, '_value', None),
            'limit_remaining': self.limit_remaining,
            'limit_total': self.limit_total
        }
