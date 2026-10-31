import asyncio
import random
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from typing import Any


class SlidingWindowRateLimiter:
    """In-memory sliding-window rate limiter with monotonic timestamp gating."""

    def __init__(self, rpm_limit: int = 60) -> None:
        self.interval = 60.0 / max(rpm_limit, 1)
        self._lock = asyncio.Lock()
        self._next_allowed_at = 0.0

    def reset(self) -> None:
        self._next_allowed_at = 0.0

    async def acquire(
        self,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Any] = asyncio.sleep,
    ) -> None:
        async with self._lock:
            now = clock()
            wait_time = max(0.0, self._next_allowed_at - now)
            if wait_time > 0:
                await sleep(wait_time)
                now = clock()
            self._next_allowed_at = max(now, self._next_allowed_at) + self.interval

    async def apply_cooldown(
        self,
        cooldown_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Any] = asyncio.sleep,
    ) -> None:
        async with self._lock:
            now = clock()
            self._next_allowed_at = max(self._next_allowed_at, now + cooldown_seconds)
            await sleep(cooldown_seconds)


def parse_retry_after(header_value: str | None) -> float | None:
    """Parse HTTP Retry-After header as seconds or HTTP-date."""
    if not header_value:
        return None
    try:
        return max(0.0, float(header_value.strip()))
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(header_value.strip())
        return max(0.0, dt.timestamp() - time.time())
    except Exception:
        return None


def calculate_jittered_backoff(
    attempt: int,
    base: float = 1.0,
    max_seconds: float = 60.0,
    jitter_factor: float = 0.5,
) -> float:
    """Calculate exponential backoff delay with random jitter."""
    exp = base * (2 ** attempt)
    delay = exp + (random.uniform(0, jitter_factor) * exp)
    return min(delay, max_seconds)
