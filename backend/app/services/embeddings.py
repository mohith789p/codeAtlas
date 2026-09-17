import asyncio
import random
import time
from collections.abc import Sequence
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import Settings
from ..logging_utils import redact_sensitive_text


from tenacity import AsyncRetrying, RetryError, retry_if_exception_type, stop_after_attempt


class _RetryableRateLimitError(Exception):
    """Internal sentinel for tenacity retrying on rate-limited responses."""


class EmbeddingProviderError(RuntimeError):
    """A provider failure that should fail the current ingestion job."""


class _ProcessEmbeddingLimiter:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._next_request_at: float | None = None
        self._cooldown_until: float | None = None

    async def acquire(self, interval: float, clock: Any, sleep: Any) -> None:
        async with self._lock:
            now = clock()
            scheduled = max(value for value in (self._next_request_at, self._cooldown_until, now) if value is not None)
            if scheduled > now:
                await sleep(scheduled - now)
                now = clock()
            self._next_request_at = max(scheduled, now) + interval

    async def apply_cooldown(self, delay: float, clock: Any, sleep: Any) -> None:
        async with self._lock:
            now = clock()
            cooldown_until = now + delay
            self._cooldown_until = max(self._cooldown_until or now, cooldown_until)

    def reset(self) -> None:
        self._next_request_at = None
        self._cooldown_until = None


_PROCESS_EMBEDDING_LIMITER = _ProcessEmbeddingLimiter()


def _reset_process_embedding_limiter() -> None:
    _PROCESS_EMBEDDING_LIMITER.reset()


class GeminiEmbeddingService:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
        clock: Any = time.monotonic,
        sleep: Any = asyncio.sleep,
        random_fn: Any = random.random,
    ) -> None:
        self.settings = settings
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=self.settings.embedding_timeout_seconds)
        self._clock = clock
        self._sleep = sleep
        self._random = random_fn
        self.request_count = 0
        self.retry_count = 0
        self.rate_limit_count = 0

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.settings.gemini_api_key:
            raise EmbeddingProviderError("GEMINI_API_KEY is not configured.")
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.settings.embedding_batch_size):
            batch = texts[start:start + self.settings.embedding_batch_size]
            vectors.extend(await self._embed_batch(self._client, batch))
        return vectors

    async def _embed_batch(self, client: httpx.AsyncClient, texts: Sequence[str]) -> list[list[float]]:
        model = f"models/{self.settings.gemini_embedding_model}"
        payload = {
            "requests": [
                {
                    "model": model,
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": self.settings.embedding_dimensions,
                }
                for text in texts
            ]
        }
        url = f"{self.settings.gemini_api_url}/models/{self.settings.gemini_embedding_model}:batchEmbedContents"
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.settings.gemini_embedding_max_retries + 1),
                retry=retry_if_exception_type(_RetryableRateLimitError),
                reraise=True,
            ):
                with attempt:
                    attempt_index = attempt.retry_state.attempt_number - 1
                    await self._wait_for_rate_limit()
                    self.request_count += 1
                    try:
                        response = await client.post(url, params={"key": self.settings.gemini_api_key}, json=payload)
                        if response.status_code == 429:
                            self.rate_limit_count += 1
                            if attempt_index >= self.settings.gemini_embedding_max_retries:
                                response.raise_for_status()
                            self.retry_count += 1
                            await self._wait_after_rate_limit(response, attempt_index)
                            raise _RetryableRateLimitError()
                        response.raise_for_status()
                        body: dict[str, Any] = response.json()
                        embeddings = body.get("embeddings")
                        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
                            raise EmbeddingProviderError("Gemini returned an unexpected embedding response.")
                        vectors = [item.get("values") for item in embeddings]
                        if any(not isinstance(vector, list) or not vector for vector in vectors):
                            raise EmbeddingProviderError("Gemini returned an empty embedding vector.")
                        if any(len(vector) != self.settings.embedding_dimensions for vector in vectors):
                            dimensions = sorted({len(vector) for vector in vectors})
                            raise EmbeddingProviderError(
                                f"Gemini returned dimensions {dimensions}; expected {self.settings.embedding_dimensions}."
                            )
                        return vectors
                    except (_RetryableRateLimitError, EmbeddingProviderError):
                        raise
                    except (httpx.HTTPError, ValueError) as exc:
                        raise EmbeddingProviderError(redact_sensitive_text(f"Gemini embedding request failed: {exc}")) from None
        except RetryError:
            raise EmbeddingProviderError("Gemini embedding retries exhausted.") from None
        raise EmbeddingProviderError("Gemini embedding retries exhausted.")

    async def _wait_for_rate_limit(self) -> None:
        interval = 60.0 / self.settings.gemini_embedding_rpm_limit
        await _PROCESS_EMBEDDING_LIMITER.acquire(interval, self._clock, self._sleep)

    async def _wait_after_rate_limit(self, response: httpx.Response, attempt: int) -> None:
        retry_after = response.headers.get("Retry-After")
        try:
            delay = float(retry_after) if retry_after is not None else None
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                delay = None
        if delay is None:
            exponential = self.settings.gemini_embedding_retry_base_seconds * (2 ** attempt)
            delay = exponential + (self._random() * exponential)
        await _PROCESS_EMBEDDING_LIMITER.apply_cooldown(
            min(delay, self.settings.gemini_embedding_retry_max_seconds), self._clock, self._sleep
        )


class LangChainEvaluationEmbeddingService:
    """LangChain-backed local embedding service reserved for evaluation validation."""

    def __init__(self, model_name: str) -> None:
        from langchain_huggingface import HuggingFaceEmbeddings

        self.model_name = model_name
        self._model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"local_files_only": True},
        )
        self.request_count = 0
        self.retry_count = 0
        self.rate_limit_count = 0

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        self.request_count += 1
        return await asyncio.to_thread(self._model.embed_documents, list(texts))
