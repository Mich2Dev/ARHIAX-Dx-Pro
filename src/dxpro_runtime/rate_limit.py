"""Token-bucket rate limiter (in-memory, thread-safe).

For multi-instance deployments, replace with a Redis-backed implementation.
The interface is identical so callers don't change.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from fastapi import HTTPException


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    """Token bucket per identifier.

    `requests_per_minute` sets steady-state rate. `burst` allows short spikes
    (defaults to one minute of capacity).
    """

    def __init__(self, *, requests_per_minute: int, burst: int | None = None) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        self.rate_per_second = requests_per_minute / 60.0
        self.capacity = float(burst if burst is not None else requests_per_minute)
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def check(self, identifier: str) -> None:
        """Consume one token for `identifier`. Raise 429 if depleted."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(identifier)
            if bucket is None:
                bucket = _Bucket(tokens=self.capacity, last_refill=now)
                self._buckets[identifier] = bucket
            else:
                elapsed = now - bucket.last_refill
                bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.rate_per_second)
                bucket.last_refill = now

            if bucket.tokens < 1.0:
                retry_after = max(1, int((1.0 - bucket.tokens) / self.rate_per_second) + 1)
                raise HTTPException(
                    status_code=429,
                    detail={"error": "rate_limited", "retry_after_seconds": retry_after},
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.tokens -= 1.0


class NullRateLimiter:
    """No-op limiter for environments where rate limiting is disabled."""

    def check(self, identifier: str) -> None:  # noqa: D401, ARG002
        return None
