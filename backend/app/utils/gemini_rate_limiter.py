"""
Multi-Window Rate Limiter for Google Gemini API.

Enforces limits across three dimensions:
- RPM: Requests Per Minute (rolling 60-second window)
- TPM: Tokens Per Minute (rolling 60-second window)
- RPD: Requests Per Day (resets at midnight UTC)
"""

import asyncio
import time
import logging
from typing import List, Tuple
from datetime import datetime, timezone

logger = logging.getLogger("gemini_rate_limiter")


class GeminiDailyQuotaExceededError(Exception):
    """Raised when the daily request limit (RPD) for Gemini API is reached."""
    pass


class GeminiRateLimiter:
    """
    Asynchronous multi-window rate limiter.
    Tracks RPM, TPM, and RPD with in-memory request queueing and daily reset.
    """

    def __init__(self, rpm_limit: int = 100, tpm_limit: int = 30000, rpd_limit: int = 1000):
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.rpd_limit = rpd_limit

        self._request_timestamps: List[float] = []
        self._token_log: List[Tuple[float, int]] = []

        self._rpd_date: str = self._current_utc_date()
        self._rpd_count: int = 0

        self._lock = asyncio.Lock()
        self._waiting_count: int = 0

    @staticmethod
    def _current_utc_date() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count: approx 4 characters = 1 token (min 1 token for non-empty text)."""
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)

    @staticmethod
    def estimate_batch_tokens(texts: List[str]) -> int:
        """Estimate total tokens across a list of texts."""
        return sum(GeminiRateLimiter.estimate_tokens(t) for t in texts)

    async def acquire(self, token_count: int = 1) -> None:
        """
        Acquires permission for 1 request with estimated token_count.
        Delays execution if RPM or TPM limits are hit.
        Raises GeminiDailyQuotaExceededError if RPD limit is hit.
        """
        async with self._lock:
            self._waiting_count += 1
            try:
                while True:
                    now = time.monotonic()

                    # 1. Check daily RPD reset
                    current_date = self._current_utc_date()
                    if current_date != self._rpd_date:
                        self._rpd_date = current_date
                        self._rpd_count = 0

                    if self._rpd_count >= self.rpd_limit:
                        logger.error(
                            f"[GeminiRateLimiter] Daily limit reached: {self._rpd_count}/{self.rpd_limit} requests today (UTC)."
                        )
                        raise GeminiDailyQuotaExceededError(
                            f"Gemini daily quota exceeded ({self._rpd_count}/{self.rpd_limit} RPD)."
                        )

                    # 2. Clean sliding window entries older than 60.0 seconds
                    cutoff = now - 60.0
                    self._request_timestamps = [ts for ts in self._request_timestamps if ts > cutoff]
                    self._token_log = [entry for entry in self._token_log if entry[0] > cutoff]

                    # 3. Calculate usage
                    current_rpm = len(self._request_timestamps)
                    current_tpm = sum(t_count for _, t_count in self._token_log)

                    logger.info(
                        f"""
                         ===== RATE LIMITER =====
                         Incoming Tokens : {token_count}
                         Current RPM     : {current_rpm}/{self.rpm_limit}
                         Current TPM     : {current_tpm}/{self.tpm_limit}
                         Current RPD     : {self._rpd_count}/{self.rpd_limit}
                         Queue Depth     : {self._waiting_count}
                       ========================
                       """
                    )

                    wait_time = 0.0

                    # Check RPM limit
                    if current_rpm >= self.rpm_limit:
                        oldest_req = self._request_timestamps[0]
                        wait_time = max(wait_time, (oldest_req + 60.0) - now + 0.05)

                    # Check TPM limit
                    if current_tpm + token_count > self.tpm_limit:
                        needed = (current_tpm + token_count) - self.tpm_limit
                        accumulated = 0
                        for ts, t_count in self._token_log:
                            accumulated += t_count
                            if accumulated >= needed:
                                wait_time = max(wait_time, (ts + 60.0) - now + 0.05)
                                break

                    if wait_time > 0:
                        logger.info(
                            f"[GeminiRateLimiter] Limit reached (RPM: {current_rpm}/{self.rpm_limit}, "
                            f"TPM: {current_tpm}+{token_count}/{self.tpm_limit}, Queue Depth: {self._waiting_count}). "
                            f"Delaying for {wait_time:.2f}s..."
                        )
                        self._lock.release()
                        try:
                            await asyncio.sleep(wait_time)
                        finally:
                            await self._lock.acquire()
                    else:
                        now_record = time.monotonic()
                        self._request_timestamps.append(now_record)
                        self._token_log.append((now_record, token_count))
                        self._rpd_count += 1

                        logger.debug(
                            f"[GeminiRateLimiter] Request acquired. RPM: {len(self._request_timestamps)}/{self.rpm_limit}, "
                            f"TPM: {current_tpm + token_count}/{self.tpm_limit}, RPD: {self._rpd_count}/{self.rpd_limit}"
                        )
                        break
            finally:
                self._waiting_count -= 1

    @property
    def current_rpm(self) -> int:
        now = time.monotonic()
        return sum(1 for ts in self._request_timestamps if (now - ts) < 60.0)

    @property
    def current_tpm(self) -> int:
        now = time.monotonic()
        return sum(t_count for ts, t_count in self._token_log if (now - ts) < 60.0)

    @property
    def current_rpd(self) -> int:
        return self._rpd_count

    @property
    def queue_depth(self) -> int:
        return self._waiting_count
