import asyncio
import time
import pytest
from app.utils.gemini_rate_limiter import GeminiRateLimiter, GeminiDailyQuotaExceededError


@pytest.mark.asyncio
async def test_token_estimation():
    """Verify token estimation calculation (~4 characters per token, min 1 for non-empty)."""
    limiter = GeminiRateLimiter()
    assert limiter.estimate_tokens("") == 0
    assert limiter.estimate_tokens("hi") == 1
    assert limiter.estimate_tokens("12345678") == 2
    assert limiter.estimate_batch_tokens(["1234", "12345678"]) == 1 + 2 == 3


@pytest.mark.asyncio
async def test_rpm_limit_delay():
    """Verify rate limiter delays execution when RPM limit is reached."""
    # Set RPM limit = 2 for quick testing
    limiter = GeminiRateLimiter(rpm_limit=2, tpm_limit=1000, rpd_limit=100)

    t0 = time.monotonic()
    await limiter.acquire(token_count=10)
    await limiter.acquire(token_count=10)
    t1 = time.monotonic()

    # The first 2 requests should be immediate (< 0.1s)
    assert t1 - t0 < 0.2
    assert limiter.current_rpm == 2

    # Override the oldest timestamp so we don't actually wait 60s in test
    limiter._request_timestamps[0] = time.monotonic() - 59.9

    t2 = time.monotonic()
    await limiter.acquire(token_count=10)
    t3 = time.monotonic()

    # The 3rd request should wait ~0.1s (until oldest timestamp ages past 60s)
    assert t3 - t2 >= 0.05
    assert t3 - t2 < 1.0


@pytest.mark.asyncio
async def test_tpm_limit_delay():
    """Verify rate limiter delays execution when TPM limit is reached."""
    # Set TPM limit = 100
    limiter = GeminiRateLimiter(rpm_limit=10, tpm_limit=100, rpd_limit=100)

    await limiter.acquire(token_count=60)
    assert limiter.current_tpm == 60

    # Age out token log entry partially
    limiter._token_log[0] = (time.monotonic() - 59.9, 60)

    t0 = time.monotonic()
    # Acquire 50 tokens (60 + 50 = 110 > 100 TPM -> must wait)
    await limiter.acquire(token_count=50)
    t1 = time.monotonic()

    assert t1 - t0 >= 0.05
    assert t1 - t0 < 1.0


@pytest.mark.asyncio
async def test_rpd_limit_exceeded():
    """Verify GeminiDailyQuotaExceededError is raised when RPD limit is reached."""
    limiter = GeminiRateLimiter(rpm_limit=100, tpm_limit=1000, rpd_limit=2)

    await limiter.acquire(token_count=10)
    await limiter.acquire(token_count=10)

    assert limiter.current_rpd == 2

    with pytest.raises(GeminiDailyQuotaExceededError) as exc_info:
        await limiter.acquire(token_count=10)

    assert "daily quota exceeded" in str(exc_info.value).lower()
