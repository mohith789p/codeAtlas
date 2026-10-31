import os
import pytest
from app.embeddings.embedding_service import EmbeddingService
from app.ingestion.step_01_github_client import GitHubClient
from app.shared.config import get_settings


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_github_metadata():
    client = GitHubClient()
    meta = await client.fetch_repository_metadata("https://github.com/octocat/Hello-World")
    assert meta["owner"] == "octocat"
    assert meta["name"] == "Hello-World"
    assert "default_branch" in meta


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_gemini_embedding():
    settings = get_settings()
    if not settings.gemini_api_key:
        pytest.skip("CODE_ATLAS_GEMINI_API_KEY is not configured.")

    service = EmbeddingService(settings=settings)
    vectors = await service.embed_documents(["def main(): return 42"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 768
    await service.aclose()
