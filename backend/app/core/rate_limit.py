from __future__ import annotations

import threading
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[tuple[str, str], list[float]] = defaultdict(list)

    def check(self, scope: str, key: str, limit: int, window_seconds: int) -> None:
        now = time.time()
        bucket_key = (scope, key)
        with self._lock:
            timestamps = [
                value
                for value in self._buckets[bucket_key]
                if now - value < window_seconds
            ]
            if len(timestamps) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded.",
                )
            timestamps.append(now)
            self._buckets[bucket_key] = timestamps


rate_limiter = InMemoryRateLimiter()


def rate_limit(
    scope: str, limit: int, window_seconds: int
) -> Callable[[Request], None]:
    def _dependency(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        rate_limiter.check(scope, client_host, limit, window_seconds)

    return _dependency
