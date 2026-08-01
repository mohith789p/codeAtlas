import pytest
from unittest.mock import AsyncMock, patch
import httpx
from app.core.gemini import GeminiClient, GeminiFatalError, GeminiRetryableError
from app.core.config import settings


@pytest.mark.asyncio
async def test_batch_chunking_splitting():
    """Verify 250 input texts are split into batches according to max_batch_size (100, 100, 50)."""
    client = GeminiClient()
    texts = [f"Text sample number {i}" for i in range(250)]

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    mock_response = httpx.Response(
        200,
        request=req,
        json={"embeddings": [{"values": [0.1] * 3072} for _ in range(100)]}
    )
    mock_response_last = httpx.Response(
        200,
        request=req,
        json={"embeddings": [{"values": [0.1] * 3072} for _ in range(50)]}
    )

    call_count = 0

    async def mock_post(url, json):
        nonlocal call_count
        call_count += 1
        num_reqs = len(json.get("requests", []))
        return httpx.Response(
            200,
            request=req,
            json={"embeddings": [{"values": [0.1] * 3072} for _ in range(num_reqs)]}
        )

    with patch.object(settings, "GEMINI_MAX_BATCH_SIZE", 100), patch("httpx.AsyncClient.post", side_effect=mock_post):
        results = await client.generate_embeddings_batch(texts)

    assert len(results) == 250
    assert call_count == 3  # 100, 100, 50
    assert all(len(vec) == 3072 for vec in results)


@pytest.mark.asyncio
async def test_batch_1to1_output_mapping():
    """Verify returned embedding vectors align 1:1 with input text order."""
    client = GeminiClient()
    texts = ["apple", "banana", "cherry"]

    mock_embeddings = [
        {"values": [1.0] + [0.0] * 3071},
        {"values": [2.0] + [0.0] * 3071},
        {"values": [3.0] + [0.0] * 3071},
    ]

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    mock_res = httpx.Response(200, request=req, json={"embeddings": mock_embeddings})

    with patch("httpx.AsyncClient.post", return_value=mock_res):
        results = await client.generate_embeddings_batch(texts)

    assert len(results) == 3
    assert results[0][0] == 1.0
    assert results[1][0] == 2.0
    assert results[2][0] == 3.0


@pytest.mark.asyncio
async def test_exponential_backoff_retry_on_429():
    """Verify retry with exponential backoff on 429 rate limit error."""
    client = GeminiClient()
    client.max_retries = 3

    request = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    res_429 = httpx.Response(429, request=request)
    res_200 = httpx.Response(200, request=request, json={"embeddings": [{"values": [0.5] * 3072}]})

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            res_429.raise_for_status()
        return res_200

    with patch("httpx.AsyncClient.post", side_effect=mock_post), \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        results = await client.generate_embeddings_batch(["test string"])

    assert len(results) == 1
    assert call_count == 3
    assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_unexpected_dimension_error():
    """Verify GeminiFatalError is raised if Gemini returns vector dimension other than 3072."""
    client = GeminiClient()
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    res_bad_dim = httpx.Response(200, request=request, json={"embeddings": [{"values": [0.1] * 768}]})

    with patch("httpx.AsyncClient.post", return_value=res_bad_dim):
        with pytest.raises(GeminiFatalError) as exc_info:
            await client.generate_embeddings_batch(["test string"])

    assert "unexpected embedding dimension" in str(exc_info.value).lower()
