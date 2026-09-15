import asyncio

import httpx
import pytest

from app.config import Settings
from app.services.embeddings import EmbeddingProviderError, GeminiEmbeddingService, _reset_process_embedding_limiter


@pytest.fixture(autouse=True)
def reset_embedding_limiter():
    _reset_process_embedding_limiter()
    yield
    _reset_process_embedding_limiter()


@pytest.mark.asyncio
async def test_gemini_embedding_maps_batch_response_and_uses_configured_key():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"embeddings": [{"values": [0.1, 0.2]}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = GeminiEmbeddingService(Settings(gemini_api_key="secret", embedding_dimensions=2, gemini_embedding_rpm_limit=600), client)
    vectors = await service.embed_documents(["hello"])
    await client.aclose()

    assert vectors == [[0.1, 0.2]]
    assert requests[0].url.params["key"] == "secret"
    assert "secret" not in str(requests[0].headers)
    assert requests[0].content.find(b'"outputDimensionality":2') >= 0


@pytest.mark.asyncio
async def test_gemini_embedding_rejects_schema_dimension_mismatch():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [{"values": [0.1, 0.2]}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = GeminiEmbeddingService(Settings(gemini_api_key="secret", embedding_dimensions=768), client)
    with pytest.raises(EmbeddingProviderError, match="expected 768"):
        await service.embed_documents(["hello"])
    await client.aclose()


@pytest.mark.asyncio
async def test_gemini_embedding_failure_is_explicit():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "quota"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = GeminiEmbeddingService(Settings(gemini_api_key="secret", gemini_embedding_max_retries=0), client)
    with pytest.raises(EmbeddingProviderError, match="Gemini embedding request failed"):
        await service.embed_documents(["hello"])
    await client.aclose()


@pytest.mark.asyncio
async def test_embedding_requests_are_paced_between_batches():
    now = [0.0]
    sleeps = []

    async def sleep(delay):
        sleeps.append(delay)
        now[0] += delay

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [{"values": [0.1, 0.2]}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = GeminiEmbeddingService(
        Settings(gemini_api_key="secret", embedding_dimensions=2, embedding_batch_size=1, gemini_embedding_rpm_limit=60),
        client,
        clock=lambda: now[0],
        sleep=sleep,
    )
    await service.embed_documents(["one", "two"])
    await client.aclose()

    assert sleeps == [1.0]
    assert service.request_count == 2


@pytest.mark.asyncio
async def test_embedding_instances_share_process_wide_limiter():
    now = [0.0]
    starts = []

    async def sleep(delay):
        now[0] += delay

    async def handler(request: httpx.Request) -> httpx.Response:
        starts.append(now[0])
        return httpx.Response(200, json={"embeddings": [{"values": [0.1, 0.2]}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(gemini_api_key="secret", embedding_dimensions=2, gemini_embedding_rpm_limit=60)
    first = GeminiEmbeddingService(settings, client, clock=lambda: now[0], sleep=sleep)
    second = GeminiEmbeddingService(settings, client, clock=lambda: now[0], sleep=sleep)
    await asyncio.gather(first.embed_documents(["one"]), second.embed_documents(["two"]))
    await client.aclose()

    assert starts == [0.0, 1.0]


@pytest.mark.asyncio
async def test_retry_from_one_instance_obeys_limiter_for_another_instance():
    now = [0.0]
    starts = []
    responses = [httpx.Response(429, headers={"Retry-After": "4"}), httpx.Response(200, json={"embeddings": [{"values": [0.1, 0.2]}]}), httpx.Response(200, json={"embeddings": [{"values": [0.1, 0.2]}]})]

    async def sleep(delay):
        now[0] += delay

    async def handler(request: httpx.Request) -> httpx.Response:
        starts.append(now[0])
        return responses.pop(0)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(gemini_api_key="secret", embedding_dimensions=2, gemini_embedding_rpm_limit=60)
    first = GeminiEmbeddingService(settings, client, clock=lambda: now[0], sleep=sleep)
    second = GeminiEmbeddingService(settings, client, clock=lambda: now[0], sleep=sleep)
    await first.embed_documents(["one"])
    await second.embed_documents(["two"])
    await client.aclose()

    assert starts == [0.0, 4.0, 5.0]
    assert first.rate_limit_count == 1
    assert first.retry_count == 1


@pytest.mark.asyncio
async def test_shared_429_cooldown_delays_subsequent_caller():
    now = [0.0]
    starts = []
    first_response = True

    async def sleep(delay):
        now[0] += delay

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal first_response
        starts.append(now[0])
        if first_response:
            first_response = False
            return httpx.Response(429, headers={"Retry-After": "5"})
        return httpx.Response(200, json={"embeddings": [{"values": [0.1, 0.2]}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(gemini_api_key="secret", embedding_dimensions=2, gemini_embedding_rpm_limit=60)
    first = GeminiEmbeddingService(settings, client, clock=lambda: now[0], sleep=sleep)
    second = GeminiEmbeddingService(settings, client, clock=lambda: now[0], sleep=sleep)
    await first._embed_batch(client, ["one"])
    await second.embed_documents(["two"])
    await client.aclose()

    assert starts == [0.0, 5.0, 6.0]


@pytest.mark.asyncio
async def test_429_respects_retry_after_and_succeeds():
    delays = []
    responses = [httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json={"embeddings": [{"values": [0.1, 0.2]}]})]

    async def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    async def sleep(delay):
        delays.append(delay)
        service_clock[0] += delay

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service_clock = [0.0]
    service = GeminiEmbeddingService(Settings(gemini_api_key="secret", embedding_dimensions=2, gemini_embedding_rpm_limit=600), client, clock=lambda: service_clock[0], sleep=sleep)
    assert await service.embed_documents(["hello"]) == [[0.1, 0.2]]
    await client.aclose()

    assert delays == [7.0]
    assert service.rate_limit_count == 1
    assert service.retry_count == 1


@pytest.mark.asyncio
async def test_429_backoff_is_bounded_and_non_429_is_not_retried():
    delays = []
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429)

    service_clock = [0.0]

    async def sleep(delay):
        delays.append(delay)
        service_clock[0] += delay

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = GeminiEmbeddingService(Settings(gemini_api_key="secret", embedding_dimensions=2, gemini_embedding_max_retries=2, gemini_embedding_retry_base_seconds=2, gemini_embedding_retry_max_seconds=3, gemini_embedding_rpm_limit=600), client, clock=lambda: service_clock[0], sleep=sleep, random_fn=lambda: 0.0)
    with pytest.raises(EmbeddingProviderError):
        await service.embed_documents(["hello"])
    await client.aclose()
    assert len(calls) == 3
    assert delays == [2.0, 3.0]

    async def server_error(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(500)

    client = httpx.AsyncClient(transport=httpx.MockTransport(server_error))
    service = GeminiEmbeddingService(Settings(gemini_api_key="secret", embedding_dimensions=2, gemini_embedding_max_retries=2, gemini_embedding_rpm_limit=600), client, clock=lambda: service_clock[0], sleep=sleep)
    with pytest.raises(EmbeddingProviderError):
        await service.embed_documents(["hello"])
    await client.aclose()
    assert len(calls) == 4


def test_embedding_configuration_keeps_model_and_dimensions():
    settings = Settings(gemini_embedding_model="gemini-embedding-001", embedding_dimensions=768, gemini_embedding_rpm_limit=60)
    assert settings.gemini_embedding_model == "gemini-embedding-001"
    assert settings.embedding_dimensions == 768
    assert settings.gemini_embedding_rpm_limit == 60
