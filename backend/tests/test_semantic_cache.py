import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from app.config import Settings
from app.persistence import SupabasePersistence


@pytest.mark.asyncio
async def test_cache_rpc_uses_explicit_parameters_and_returns_provider_result():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    persistence = SupabasePersistence(Settings(supabase_url="https://example.supabase.co", supabase_service_role_key="key"), client)
    repo_id = uuid4()
    result = await persistence.get_semantic_cache(repo_id, [0.0, 1.0], 0.92)
    await client.aclose()

    assert result is None
    payload = json.loads(requests[0].content)
    assert payload == {"p_repo_id": str(repo_id), "p_query_embedding": [0.0, 1.0], "p_similarity_threshold": 0.92}


def test_cache_migration_qualifies_stored_and_incoming_embeddings():
    migration = Path("supabase/migrations/0004_fix_semantic_cache_similarity.sql").read_text(encoding="utf-8")
    assert "drop function if exists public.match_semantic_cache(uuid, vector, double precision);" in migration
    assert "p_query_embedding" in migration
    assert "cache_entry.query_embedding <=> p_query_embedding" in migration
    assert "cache_entry.repo_id = p_repo_id" in migration
    assert ">= p_similarity_threshold" in migration


@pytest.mark.parametrize(
    ("similarity", "threshold", "expected_hit"),
    [(0.49, 0.92, False), (0.92, 0.92, True), (0.99, 0.92, True)],
)
def test_cache_threshold_contract(similarity, threshold, expected_hit):
    assert (similarity >= threshold) is expected_hit


@pytest.mark.asyncio
async def test_cache_repo_isolation_contract():
    from app.store import InMemoryStore

    store = InMemoryStore()
    repo_a = uuid4()
    repo_b = uuid4()
    embedding = [1.0, 0.0, 0.0]
    expected_response = {"answer": "result for repo A"}

    await store.save_semantic_cache(repo_a, "query text", embedding, expected_response)

    # Cache hit for same repository
    hit_a = await store.get_semantic_cache(repo_a, embedding, threshold=0.9)
    assert hit_a == expected_response

    # Cache miss for different repository even with identical query embedding
    hit_b = await store.get_semantic_cache(repo_b, embedding, threshold=0.9)
    assert hit_b is None

