import pytest
from app.shared.config import Settings
from app.shared.exceptions import CodeAtlasError, IngestionError, PersistenceError, RateLimitExceededError
from app.shared.logging import RedactingFormatter, redact_sensitive, redact_sensitive_text
from app.shared.observability import create_runnable_config, safe_traceable, setup_langsmith_environment
from app.shared.rate_limiter import SlidingWindowRateLimiter, calculate_jittered_backoff, parse_retry_after


def test_settings_properties():
    cfg = Settings(cors_origins="http://localhost:3000, http://example.com")
    assert cfg.allowed_origins == ["http://localhost:3000", "http://example.com"]
    assert cfg.embedding_dimensions == 768


def test_secret_redaction():
    text = "error: https://api.com?key=AIzaSySecret and Bearer eyJhbGciOi token"
    redacted = redact_sensitive_text(text)
    assert "AIzaSySecret" not in redacted
    assert "eyJhbGciOi" not in redacted
    assert "[REDACTED]" in redacted

    data = {"secret": "secret123", "nested": ["Bearer secret456"]}
    safe_data = redact_sensitive(data)
    assert safe_data["secret"] == "[REDACTED]"
    assert "[REDACTED]" in safe_data["nested"][0]


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter():
    limiter = SlidingWindowRateLimiter(rpm_limit=120)
    await limiter.acquire()
    assert parse_retry_after("10") == 10.0
    assert parse_retry_after(None) is None
    delay = calculate_jittered_backoff(attempt=2, base=0.1, max_seconds=10.0)
    assert 0.4 <= delay <= 2.0


def test_domain_exceptions_hierarchy():
    exc = IngestionError("Corrupt zip", {"repo": "test/repo"})
    assert isinstance(exc, CodeAtlasError)
    assert exc.message == "Corrupt zip"
    assert exc.details["repo"] == "test/repo"
    assert issubclass(PersistenceError, CodeAtlasError)
    assert issubclass(RateLimitExceededError, CodeAtlasError)


@pytest.mark.asyncio
async def test_observability_safe_wrappers():
    cfg = create_runnable_config(tags=["test"], metadata={"api_key": "secret123"})
    assert "test" in cfg["tags"]
    assert cfg["metadata"]["api_key"] == "[REDACTED]"

    @safe_traceable(name="dummy_task")
    async def dummy():
        return 42

    assert await dummy() == 42
