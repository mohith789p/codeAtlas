from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest

from app.embeddings.embedding_service import EmbeddingService
from app.shared.config import Settings
from app.shared.exceptions import ConfigurationError, ProviderError


@pytest.mark.asyncio
async def test_embed_documents_empty_returns_empty():
    service = EmbeddingService(settings=Settings())
    assert await service.embed_documents([]) == []


@pytest.mark.asyncio
async def test_embed_documents_missing_api_key():
    service = EmbeddingService(settings=Settings(gemini_api_key=None))
    with pytest.raises(ConfigurationError):
        await service.embed_documents(["sample code"])


@pytest.mark.asyncio
async def test_embed_batch_success():
    settings = Settings(
        gemini_api_key="test-key",
        gemini_api_url="https://generativelanguage.googleapis.com/v1beta",
        gemini_embedding_model="gemini-embedding-001",
        embedding_dimensions=768,
        embedding_batch_size=2,
    )
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False

    fake_vector = [0.01] * 768
    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "embeddings": [{"values": fake_vector}, {"values": fake_vector}]
    }
    mock_client.post = AsyncMock(return_value=fake_response)

    service = EmbeddingService(settings=settings, client=mock_client)
    results = await service.embed_documents(["code 1", "code 2"])

    assert len(results) == 2
    assert len(results[0]) == 768
    assert results[0] == fake_vector
    mock_client.post.assert_called_once()
