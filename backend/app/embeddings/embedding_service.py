import asyncio
import logging
from collections.abc import Sequence
from typing import Any
import httpx

from app.shared.config import Settings, get_settings
from app.shared.exceptions import ConfigurationError, ProviderError
from app.shared.rate_limiter import SlidingWindowRateLimiter, calculate_jittered_backoff, parse_retry_after

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Batch embedding service using Gemini with rate-limiting and retries."""

    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings or get_settings()
        self._owns_client = client is None
        self._client = client
        self.limiter = SlidingWindowRateLimiter(self.settings.gemini_embedding_rpm_limit)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.settings.embedding_timeout_seconds)
            self._owns_client = True
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.settings.gemini_api_key:
            raise ConfigurationError("Gemini API key is required for embeddings.")
        vectors: list[list[float]] = []
        batch_size = max(self.settings.embedding_batch_size, 1)
        for i in range(0, len(texts), batch_size):
            batch = list(texts[i : i + batch_size])
            vectors.extend(await self._embed_batch_with_retry(batch))
        return vectors

    async def _embed_batch_with_retry(self, texts: list[str]) -> list[list[float]]:
        model = f"models/{self.settings.gemini_embedding_model}"
        url = f"{self.settings.gemini_api_url}/{model}:batchEmbedContents"
        payload = {
            "requests": [
                {"model": model, "content": {"parts": [{"text": t}]}, "outputDimensionality": self.settings.embedding_dimensions}
                for t in texts
            ]
        }
        client = self._get_client()
        for attempt in range(self.settings.gemini_embedding_max_retries + 1):
            await self.limiter.acquire()
            try:
                resp = await client.post(url, params={"key": self.settings.gemini_api_key}, json=payload)
                if resp.status_code == 429:
                    retry_sec = parse_retry_after(resp.headers.get("Retry-After")) or calculate_jittered_backoff(attempt)
                    logger.warning("Gemini 429 rate limit hit; waiting %.1fs (attempt %d)", retry_sec, attempt)
                    await self.limiter.apply_cooldown(retry_sec)
                    continue
                resp.raise_for_status()
                data = resp.json()
                embeddings = data.get("embeddings", [])
                vectors = [item.get("values", []) for item in embeddings]
                if len(vectors) != len(texts):
                    raise ProviderError(f"Expected {len(texts)} embeddings, got {len(vectors)}")
                return vectors
            except (httpx.HTTPError, ValueError) as exc:
                if attempt == self.settings.gemini_embedding_max_retries:
                    raise ProviderError(f"Gemini embedding batch failed: {exc}") from exc
                await asyncio.sleep(calculate_jittered_backoff(attempt))
        raise ProviderError("Gemini embedding retries exhausted.")
