import os
from uuid import UUID

import httpx
import pytest

from app.config import Settings
from app.models import IngestionStatus, Repository, RepositoryStats
from app.persistence import SupabasePersistence
from app.services.embeddings import GeminiEmbeddingService
from app.services.reranking import CrossEncoderReranker
from app.services.retrieval import RetrievalService
from app.main import app
from app.store import store


@pytest.mark.live
@pytest.mark.asyncio
async def test_real_retrieval_uses_indexed_repository_and_returns_structural_metadata():
    settings = Settings()
    if not settings.gemini_api_key or not settings.supabase_url or not settings.supabase_service_role_key:
        pytest.fail("Live retrieval requires Gemini and Supabase environment variables.")
    repository_id = os.getenv("CODE_ATLAS_RETRIEVAL_REPOSITORY_ID")
    if not repository_id:
        pytest.fail("Set CODE_ATLAS_RETRIEVAL_REPOSITORY_ID to a ready repository UUID from Supabase.")

    service = RetrievalService(
        SupabasePersistence(settings),
        GeminiEmbeddingService(settings),
        CrossEncoderReranker(settings.reranker_model),
    )
    base_url = settings.supabase_url.rstrip("/")
    if not base_url.endswith("/rest/v1"):
        base_url += "/rest/v1"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        clear_cache_response = await client.delete(
            f"{base_url}/semantic_cache?repo_id=eq.{repository_id}",
            headers=headers,
        )
    assert clear_cache_response.status_code in {200, 204}
    query = os.getenv("CODE_ATLAS_RETRIEVAL_QUERY", "Where is the main entry point?")
    result = await service.retrieve(UUID(repository_id), query)
    cached_result = await service.retrieve(UUID(repository_id), query)

    assert result["cache_hit"] is False
    assert cached_result["cache_hit"] is True
    assert result["dense_count"] <= 20
    assert result["sparse_count"] <= 20
    assert result["retrieval_candidates"] <= 15
    assert result["reranked_count"] <= 5
    assert len(result["results"]) <= 5
    for item in result["results"]:
        assert item["repo_id"] == UUID(repository_id) or str(item["repo_id"]) == repository_id
        assert item["filepath"]
        assert "start_line" in item
        assert "end_line" in item

    store.repositories[UUID(repository_id)] = Repository(
        id=UUID(repository_id),
        name="visual-interpreter",
        url="https://github.com/mohith789p/visual-interpreter",
        status=IngestionStatus.READY,
        stats=RepositoryStats(),
    )

    async with httpx.AsyncClient(timeout=30) as client:
        clear_api_cache_response = await client.delete(
            f"{base_url}/semantic_cache?repo_id=eq.{repository_id}",
            headers=headers,
        )
    assert clear_api_cache_response.status_code in {200, 204}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        api_response = await client.post(
            f"/api/repositories/{repository_id}/retrieve",
            json={"query": query + " api"},
        )
    assert api_response.status_code == 200
    api_payload = api_response.json()
    assert "latency_ms" in api_payload
    assert "dense" in api_payload["latency_ms"]
    assert "sparse" in api_payload["latency_ms"]
    assert "reranking" in api_payload["latency_ms"]

    async with httpx.AsyncClient(timeout=30) as client:
        log_response = await client.get(
            f"{base_url}/logs?repo_id=eq.{repository_id}&stage=eq.retrieval&select=stage,latency_ms,metadata&order=created_at.desc&limit=1",
            headers=headers,
        )
    assert log_response.status_code == 200
    assert log_response.json()
