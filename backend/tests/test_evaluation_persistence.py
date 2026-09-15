import json
from uuid import uuid4

import httpx
import pytest

from app.config import Settings
from app.persistence import SupabasePersistence
from app.services.evaluation import EvaluationExample, GroundTruth


@pytest.mark.asyncio
async def test_supabase_evaluation_persistence_uses_versioned_stable_ground_truth():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST" and request.url.path.endswith("/eval_results"):
            return httpx.Response(201, json=[{"id": str(uuid4())}])
        return httpx.Response(204)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    persistence = SupabasePersistence(Settings(supabase_url="https://example.supabase.co", supabase_service_role_key="service-key"), client)
    repo_id = uuid4()
    example = EvaluationExample("What does run do?", "It returns 42.", GroundTruth("a" * 64, "src/run.py", "run", "function_definition", 1, 1), 0.9, [0.1, 0.2])

    assert await persistence.claim_evaluation(repo_id, "version-1") is True
    await persistence.save_golden_examples(repo_id, "version-1", [example])
    await persistence.finish_evaluation(repo_id, "version-1", {"status": "completed", "query_count": 1, "recall_at_5": 1.0, "precision_at_5": 0.2, "mrr": 1.0, "latency_stats": {}, "per_query": []})
    await client.aclose()

    golden_request = next(request for request in requests if request.url.path.endswith("/eval_golden_set"))
    golden = json.loads(golden_request.content)[0]
    assert golden["ground_truth"]["content_hash"] == "a" * 64
    assert golden["ground_truth"]["symbol"] == "run"
    assert "chunk_id" not in golden["ground_truth"]


@pytest.mark.asyncio
async def test_failed_evaluation_version_can_be_reclaimed_but_completed_cannot():
    requests = []
    statuses = [{"status": "failed"}]

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=statuses)
        return httpx.Response(204)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    persistence = SupabasePersistence(Settings(supabase_url="https://example.supabase.co", supabase_service_role_key="service-key"), client)
    repo_id = uuid4()

    assert await persistence.claim_evaluation(repo_id, "failed-version") is True
    assert requests[1].method == "PATCH"

    statuses[:] = [{"status": "completed"}]
    assert await persistence.claim_evaluation(repo_id, "completed-version") is False
    await client.aclose()
