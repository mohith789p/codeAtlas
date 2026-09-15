import os
from uuid import UUID, uuid4

import httpx
import pytest

from app.config import Settings
from app.persistence import SupabasePersistence
from app.services.evaluation import build_evaluation_service


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_evaluation_small_subset_persists_metrics():
    settings = Settings()
    repository_id = os.getenv("CODE_ATLAS_RETRIEVAL_REPOSITORY_ID")
    if not settings.gemini_api_key or not settings.supabase_url or not settings.supabase_service_role_key or not repository_id:
        pytest.fail("Live evaluation requires Gemini, Supabase, and CODE_ATLAS_RETRIEVAL_REPOSITORY_ID.")
    repo_id = UUID(repository_id)
    persistence = SupabasePersistence(settings)
    service = build_evaluation_service(settings, persistence)
    version = "live-" + uuid4().hex[:12]

    result = await service.evaluate_once(repo_id, eval_version=version, limit=5)

    assert result is not None
    assert result["generated_count"] > 0
    assert result["accepted_count"] > 0
    assert result["query_count"] == result["successful_count"]
    assert 0.0 <= result["recall_at_5"] <= 1.0
    assert 0.0 <= result["precision_at_5"] <= 1.0
    assert 0.0 <= result["mrr"] <= 1.0
    assert result["latency_stats"]["average"] >= 0

    base_url = settings.supabase_url.rstrip("/")
    base_url = base_url if base_url.endswith("/rest/v1") else base_url + "/rest/v1"
    headers = {"apikey": settings.supabase_service_role_key, "Authorization": f"Bearer {settings.supabase_service_role_key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        result_response = await client.get(f"{base_url}/eval_results?repo_id=eq.{repo_id}&eval_version=eq.{version}&select=status,recall_at_5,precision_at_5,mrr", headers=headers)
        golden_response = await client.get(f"{base_url}/eval_golden_set?repo_id=eq.{repo_id}&eval_version=eq.{version}&select=ground_truth,validation_score", headers=headers)
    assert result_response.status_code == 200
    assert golden_response.status_code == 200
    assert result_response.json()[0]["status"] == "completed"
    assert golden_response.json()