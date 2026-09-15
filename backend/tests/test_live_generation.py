import os
from uuid import UUID

import httpx
import pytest

from app.config import Settings
from app.main import app
from app.models import ChatSession, Repository
from app.store import store


@pytest.mark.live
@pytest.mark.asyncio
async def test_real_generation_returns_validated_retrieved_citation():
    settings = Settings()
    repository_id = os.getenv("CODE_ATLAS_RETRIEVAL_REPOSITORY_ID")
    if not settings.gemini_api_key or not repository_id:
        pytest.fail("Live generation requires Gemini credentials and CODE_ATLAS_RETRIEVAL_REPOSITORY_ID.")
    repo_id = UUID(repository_id)
    store.repositories[repo_id] = store.repositories.get(repo_id) or Repository(
        id=repo_id,
        name="visual-interpreter",
        url="https://github.com/mohith789p/visual-interpreter",
    )
    session = ChatSession(repository_id=repo_id)
    await store.save_session(session)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/chat/sessions/{session.id}/messages",
            json={"content": os.getenv("CODE_ATLAS_GENERATION_QUERY", "Where is the main function?")},
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["role"] == "assistant"
    assert payload["content"]
    assert payload["citations"]
    citation = payload["citations"][0]
    assert citation["file"]
    assert citation["line_start"] <= citation["line_end"]
    assert citation["chunk_id"]
