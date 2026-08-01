"""
Async sliding-window rate limiter module for Gemini API quota management.
Re-exports GeminiRateLimiter and GeminiDailyQuotaExceededError.
"""

from app.utils.gemini_rate_limiter import (
    GeminiRateLimiter,
    GeminiDailyQuotaExceededError,
)
from app.core.config import settings

# Shared singleton rate limiter instance configured from app settings
embedding_rate_limiter = GeminiRateLimiter(
    rpm_limit=settings.GEMINI_RPM_LIMIT,
    tpm_limit=settings.GEMINI_TPM_LIMIT,
    rpd_limit=settings.GEMINI_RPD_LIMIT,
)

# Alias for backward compatibility
RateLimiter = GeminiRateLimiter
