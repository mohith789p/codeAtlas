import httpx
import asyncio
import logging
from typing import List, Optional
from app.core.config import settings

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
        self.max_retries = 3

    @property
    def api_key(self) -> str:
        return settings.get_gemini_api_key()

    async def _execute_with_retry(self, request_func, action_desc: str):
        """Executes HTTP request with exponential backoff for 5xx/429 errors, fails fast on 4xx errors."""
        key = self.api_key
        if not key:
            raise GeminiFatalError("Gemini API Key is not configured. Please set GEMINI_API_KEY in .env file.")

        backoff = 1.0  # initial 1 second delay
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return await request_func(key)
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                # 4xx client errors (400, 401, 403, 404) are fatal -> stop immediately without retrying
                if 400 <= status_code < 500 and status_code != 429:
                    logger.error(f"[Gemini API] Fatal Client Error {status_code} during {action_desc}: {e}")
                    raise GeminiFatalError(
                        f"Gemini API Error ({status_code} {e.response.reason_phrase}). Please check your API key and model availability."
                    ) from e
                
                # 429 (Rate Limit) or 5xx (Server Error) -> retryable
                logger.warning(
                    f"[Gemini API] Attempt {attempt}/{self.max_retries} failed for {action_desc} (HTTP {status_code}). Retrying in {backoff:.1f}s..."
                )
                last_exception = e
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"[Gemini API] Attempt {attempt}/{self.max_retries} network error for {action_desc}: {e}. Retrying in {backoff:.1f}s..."
                )
                last_exception = e

            if attempt < self.max_retries:
                await asyncio.sleep(backoff)
                backoff *= 2.0  # exponential backoff

        raise GeminiRetryableError(
            f"Gemini API service unavailable after {self.max_retries} attempts ({action_desc}): {last_exception}"
        )

    async def generate_embedding(self, text: str) -> List[float]:
        """Generates 768-dimensional embedding vector for input text with fail-fast & retry logic."""

        async def _make_request(key: str):
            # Primary model: text-embedding-004
            url = f"{self.base_url}/text-embedding-004:embedContent?key={key}"
            payload = {
                "model": "models/text-embedding-004",
                "content": {"parts": [{"text": text[:8000]}]}
            }

            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 404:
                    # Fallback model if text-embedding-004 is 404 in region
                    url_fallback = f"{self.base_url}/embedding-001:embedContent?key={key}"
                    payload_fb = {
                        "model": "models/embedding-001",
                        "content": {"parts": [{"text": text[:8000]}]}
                    }
                    res = await client.post(url_fallback, json=payload_fb)

                res.raise_for_status()
                data = res.json()
                embedding = data.get("embedding", {}).get("values", [])
                if len(embedding) < 768:
                    embedding += [0.0] * (768 - len(embedding))
                return embedding[:768]

        return await self._execute_with_retry(_make_request, "embedding generation")

    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generates natural language response from Gemini with fail-fast & retry logic."""

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
