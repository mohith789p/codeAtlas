import os
from uuid import uuid4

import httpx
import pytest

from app.config import Settings
from app.models import IngestionStatus, Repository
from app.persistence import SupabasePersistence
from app.services.ingestion import run_ingestion
from app.store import InMemoryStore


@pytest.mark.live
@pytest.mark.asyncio
async def test_real_repository_ingestion_and_hash_reuse():
    settings = Settings()
    if not settings.gemini_api_key or not settings.supabase_url or not settings.supabase_service_role_key:
        pytest.fail("Live smoke test requires Gemini and Supabase environment variables.")

    repository_url = os.getenv(
        "CODE_ATLAS_SMOKE_REPOSITORY_URL",
        "https://github.com/mohith789p/visual-interpreter",
    )
    repository = Repository(id=uuid4(), name="visual-interpreter", url=repository_url)
    persistence = SupabasePersistence(settings)
    store = InMemoryStore(persistence=persistence)

    first = await run_ingestion(repository, None, store, settings)
    assert repository.status is IngestionStatus.READY
    assert first and first["total"] > 0
    assert first["embedded"] == first["total"]
    assert store.repository_documents[repository.id]
    assert any(document.metadata.get("symbol") for document in store.repository_documents[repository.id])

    second = await run_ingestion(repository, None, store, settings)
    assert repository.status is IngestionStatus.READY
    assert second and second["total"] == first["total"]
    assert second["embedded"] == 0
    assert second["reused"] == first["total"]

    base_url = settings.supabase_url.rstrip("/")
    if not base_url.endswith("/rest/v1"):
        base_url += "/rest/v1"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{base_url}/chunks?repo_id=eq.{repository.id}&select=content_hash,embedding,chunk_metadata(*)",
            headers=headers,
        )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == first["total"]
    assert all(row["embedding"] for row in rows)
    assert all(row["chunk_metadata"] for row in rows)
