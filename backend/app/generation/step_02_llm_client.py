import logging
from typing import Any
import httpx

from app.shared.config import Settings, get_settings
from app.shared.exceptions import ProviderError

logger = logging.getLogger(__name__)


class LLMClientChain:
    """4-tier resilient provider fallback: Gemini -> Groq -> Cerebras -> OpenRouter."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def generate(self, system_prompt: str, user_prompt: str) -> tuple[str, str, str]:
        """Invoke LLM chain with automatic sequential fallback across providers."""
        providers = [
            ("gemini", self._call_gemini),
            ("groq", self._call_groq),
            ("cerebras", self._call_cerebras),
            ("openrouter", self._call_openrouter),
        ]
        errors: list[str] = []
        for name, fn in providers:
            try:
                text, model = await fn(system_prompt, user_prompt)
                if text and text.strip():
                    return text.strip(), name, model
            except Exception as exc:
                logger.warning("Provider '%s' failed: %s; attempting fallback", name, exc)
                errors.append(f"{name}: {exc}")

        raise ProviderError(f"All LLM fallback providers failed: {'; '.join(errors)}")

    async def _call_gemini(self, system: str, user: str) -> tuple[str, str]:
        if not self.settings.gemini_api_key:
            raise ProviderError("Gemini API key missing")
        url = f"{self.settings.gemini_api_url}/models/{self.settings.gemini_generation_model}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, params={"key": self.settings.gemini_api_key}, json=payload)
            res.raise_for_status()
            data = res.json()
            candidates = data.get("candidates", [])
            text = candidates[0]["content"]["parts"][0]["text"]
            return text, self.settings.gemini_generation_model

    async def _call_openai_compatible(self, base_url: str, key: str | None, model: str, system: str, user: str) -> tuple[str, str]:
        if not key:
            raise ProviderError(f"Key missing for {base_url}")
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"], model

    async def _call_groq(self, system: str, user: str) -> tuple[str, str]:
        return await self._call_openai_compatible(self.settings.groq_api_url, self.settings.groq_api_key, self.settings.groq_generation_model, system, user)

    async def _call_cerebras(self, system: str, user: str) -> tuple[str, str]:
        return await self._call_openai_compatible(self.settings.cerebras_api_url, self.settings.cerebras_api_key, self.settings.cerebras_generation_model, system, user)

    async def _call_openrouter(self, system: str, user: str) -> tuple[str, str]:
        return await self._call_openai_compatible(self.settings.openrouter_api_url, self.settings.openrouter_api_key, self.settings.openrouter_generation_model, system, user)

    async def stream_generate(self, system_prompt: str, user_prompt: str):
        """Yield tokens by streaming from the LLM with fallback buffering."""
        try:
            full_text, provider, model = await self.generate(system_prompt, user_prompt)
            # Yield in word chunks to ensure consistent token-by-token streaming
            words = full_text.split(" ")
            for i, w in enumerate(words):
                yield w if i == len(words) - 1 else w + " "
        except Exception as exc:
            logger.warning("Stream generation failed: %s", exc)
            raise
