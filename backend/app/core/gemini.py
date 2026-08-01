import httpx
import asyncio
import logging
import random
import json
from typing import List, Optional
from app.core.config import settings
from app.utils.gemini_rate_limiter import (
    GeminiRateLimiter,
    GeminiDailyQuotaExceededError,
)

logger = logging.getLogger("gemini_service")


class GeminiAPIError(Exception):
    """Base exception for Gemini API errors."""
    pass


class GeminiFatalError(GeminiAPIError):
    """Fatal error (4xx client error like 401, 403, 404) - Do not retry."""
    pass


class GeminiRetryableError(GeminiAPIError):
    """Temporary error (5xx server error, 429 rate limit, network timeout) - Retryable."""
    pass


class GeminiClient:
    def __init__(self):
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.max_retries = 4
        self.rate_limiter = GeminiRateLimiter(
            rpm_limit=settings.GEMINI_RPM_LIMIT,
            tpm_limit=settings.GEMINI_TPM_LIMIT,
            rpd_limit=settings.GEMINI_RPD_LIMIT,
        )

    @property
    def api_key(self) -> str:
        return settings.get_gemini_api_key()

    @property
    def embedding_model(self) -> str:
        model = settings.GEMINI_EMBEDDING_MODEL or "gemini-embedding-001"
        return model.replace("models/", "")

    async def _execute_with_retry(self, request_func, action_desc: str):
        """Executes HTTP request with exponential backoff + jitter for 5xx/429 errors, fails fast on 4xx errors."""
        key = self.api_key
        if not key:
            raise GeminiFatalError("Gemini API Key is not configured. Please set GEMINI_API_KEY in .env file.")

        base_backoff = 20.0
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return await request_func(key)
            except (GeminiDailyQuotaExceededError, GeminiFatalError):
                raise
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                # 4xx client errors (400, 401, 403, 404) are fatal -> stop immediately without retrying
                if 400 <= status_code < 500 and status_code != 429:
                    logger.error(f"[Gemini API] Fatal Client Error {status_code} during {action_desc}: {e}")
                    raise GeminiFatalError(
                        f"Gemini API Error ({status_code} {e.response.reason_phrase}). Please check your API key and model availability."
                    ) from e

                # 429 (Rate Limit) or 5xx (Server Error) -> retryable with exponential backoff + jitter
                jitter = random.uniform(0.0, 0.5)
                backoff = base_backoff * (2 ** (attempt - 1)) + jitter
                logger.warning(
                    f"[Gemini API] Attempt {attempt}/{self.max_retries} failed for {action_desc} (HTTP {status_code}). "
                    f"Retrying in {backoff:.2f}s..."
                )
                last_exception = e
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                jitter = random.uniform(0.0, 0.5)
                backoff = base_backoff * (2 ** (attempt - 1)) + jitter
                logger.warning(
                    f"[Gemini API] Attempt {attempt}/{self.max_retries} network error for {action_desc}: {e}. "
                    f"Retrying in {backoff:.2f}s..."
                )
                last_exception = e

            if attempt < self.max_retries:
                await asyncio.sleep(backoff)

        raise GeminiRetryableError(
            f"Gemini API service unavailable after {self.max_retries} attempts ({action_desc}): {last_exception}"
        )

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates 3072-dimensional embedding vectors for a list of input texts using 
        batching (`batchEmbedContents`), rate limiting, and retry handling.
        Returns exact 3072-dimensional float vectors returned by Gemini matching `texts` 1:1 in order.
        """
        if not texts:
            return []

        max_batch_size = min(settings.GEMINI_MAX_BATCH_SIZE, 250)
        all_embeddings: List[List[float]] = []

        batches = [texts[i:i + max_batch_size] for i in range(0, len(texts), max_batch_size)]
        logger.info(
            f"[GeminiClient] Splitting {len(texts)} texts into {len(batches)} batch request(s) "
            f"(max_batch_size={max_batch_size}, expected_dim={settings.EMBEDDING_DIMENSION})."
        )

        for batch_idx, sub_batch in enumerate(batches):
            tokens = GeminiRateLimiter.estimate_batch_tokens(sub_batch)

            total_chars = sum(len(t) for t in sub_batch)
            avg_chars = total_chars / len(sub_batch)
            max_chars = max(len(t) for t in sub_batch)
            min_chars = min(len(t) for t in sub_batch)

            print(
                "\n"
                "========== GEMINI BATCH ==========\n"
                f"Batch           : {batch_idx + 1}/{len(batches)}\n"
                f"Items           : {len(sub_batch)}\n"
                f"Expected Dim    : {settings.EMBEDDING_DIMENSION}\n"
                f"EstimatedTokens : {tokens}\n"
                f"TotalChars      : {total_chars}\n"
                f"AverageChars    : {avg_chars:.2f}\n"
                f"MinChars        : {min_chars}\n"
                f"MaxChars        : {max_chars}\n"
                "=================================="
            , flush=True)

            for i, txt in enumerate(sub_batch[:5]):
                print(
                    f"Chunk {i+1}: chars={len(txt)}, est_tokens={GeminiRateLimiter.estimate_tokens(txt)}"
                , flush=True)

            await self.rate_limiter.acquire(token_count=tokens)

            async def _make_batch_request(key: str):
                model_name = self.embedding_model
                full_model = f"models/{model_name}"
                url = f"{self.base_url}/{model_name}:batchEmbedContents?key={key}"

                payload = {
                    "requests": [
                        {
                            "model": full_model,
                            "content": {"parts": [{"text": t[:8000]}]}
                        }
                        for t in sub_batch
                    ]
                }

                payload_json = json.dumps(payload)

                print(
                    "\n"
                    "========== GEMINI REQUEST ==========\n"
                    f"URL             : {url}\n"
                    f"Model           : {full_model}\n"
                    f"PayloadBytes    : {len(payload_json.encode('utf-8'))}\n"
                    f"Requests        : {len(payload['requests'])}\n"
                    "===================================="
                , flush=True)

                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.post(url, json=payload)
                    
                    if res.status_code == 404 and model_name != "gemini-embedding-2":
                        # Fallback to gemini-embedding-2 if primary model returns 404
                        fallback_url = f"{self.base_url}/gemini-embedding-2:batchEmbedContents?key={key}"
                        fallback_payload = {
                            "requests": [
                                {
                                    "model": "models/gemini-embedding-2",
                                    "content": {"parts": [{"text": t[:8000]}]}
                                }
                                for t in sub_batch
                            ]
                        }
                        res = await client.post(fallback_url, json=fallback_payload)
                        
                    if res.status_code != 200:
                        print(
                            "\n"
                            "========== GEMINI ERROR ==========\n"
                            f"Status : {res.status_code}\n"
                            f"Body:\n{res.text}\n"
                            "=================================="
                        , flush=True)

                    res.raise_for_status()
                    data = res.json()
                    raw_embeddings = data.get("embeddings", [])
                    
                    if len(raw_embeddings) != len(sub_batch):
                        raise GeminiFatalError(
                            f"Gemini batch embedding mismatch: batch size was {len(sub_batch)}, "
                            f"but received {len(raw_embeddings)} embeddings from API."
                        )

                    received_dim = len(raw_embeddings[0].get("values", [])) if raw_embeddings else 0

                    logger.info(
                        f"[GeminiClient] Batch size: {len(sub_batch)} | "
                        f"Expected dimension: {settings.EMBEDDING_DIMENSION} | "
                        f"Received dimension: {received_dim}"
                    )
                    print(
                        f"Gemini returned {len(raw_embeddings)} embedding(s).\n"
                        f"Expected dimension: {settings.EMBEDDING_DIMENSION}\n"
                        f"Received dimension: {received_dim}\n"
                        f"Batch size: {len(sub_batch)}"
                    , flush=True)

                    batch_vectors: List[List[float]] = []

                    for idx, emb_item in enumerate(raw_embeddings):
                        vec = emb_item.get("values", [])
                        rec_len = len(vec)
                        if rec_len != settings.EMBEDDING_DIMENSION:
                            raise GeminiFatalError(
                                f"Gemini API returned unexpected embedding dimension for batch item {idx}: "
                                f"expected {settings.EMBEDDING_DIMENSION}, received {rec_len}."
                            )
                        batch_vectors.append(vec)

                    return batch_vectors

            batch_res = await self._execute_with_retry(
                _make_batch_request,
                f"batch embedding generation (batch {batch_idx + 1}/{len(batches)}, {len(sub_batch)} items)"
            )
            all_embeddings.extend(batch_res)

        return all_embeddings

    async def generate_embedding(self, text: str) -> List[float]:
        """Generates 3072-dimensional embedding vector for single input text."""
        res = await self.generate_embeddings_batch([text])
        if not res or len(res[0]) != settings.EMBEDDING_DIMENSION:
            raise GeminiFatalError(
                f"Unexpected single embedding dimension from Gemini: "
                f"expected {settings.EMBEDDING_DIMENSION}, got {len(res[0]) if res else 0}"
            )
        return res[0]

    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generates natural language response from Gemini with fail-fast & retry logic."""
        tokens = GeminiRateLimiter.estimate_tokens(prompt)
        await self.rate_limiter.acquire(token_count=tokens)

        async def _make_request(key: str):
            url = f"{self.base_url}/gemini-1.5-flash:generateContent?key={key}"
            contents = [{"parts": [{"text": prompt}]}]
            payload = {"contents": contents}
            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    url2 = f"{self.base_url}/gemini-2.5-flash:generateContent?key={key}"
                    res = await client.post(url2, json=payload)
                
                res.raise_for_status()
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                return "No response generated from model."

        try:
            return await self._execute_with_retry(_make_request, "text generation")
        except GeminiAPIError as e:
            return f"Gemini AI Service Error: {str(e)}"


gemini_client = GeminiClient()
