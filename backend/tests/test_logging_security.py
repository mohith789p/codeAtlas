from uuid import uuid4

import pytest

from app.store import InMemoryStore


@pytest.mark.asyncio
async def test_event_logging_redacts_provider_credentials():
    store = InMemoryStore()
    query_secret = "query-secret-value"
    bearer_secret = "bearer-secret-value"

    await store.log_event(
        uuid4(),
        "provider_failed",
        "error",
        f"request failed: https://provider.test/generate?key={query_secret}",
        {"error": f"Authorization: Bearer {bearer_secret}"},
    )

    event_text = repr(store.logs[-1])
    assert query_secret not in event_text
    assert bearer_secret not in event_text
    assert "[REDACTED]" in event_text