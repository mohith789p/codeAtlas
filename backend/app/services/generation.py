import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import httpx

from ..config import Settings
from ..logging_utils import redact_sensitive_text
from .memory import ConversationMemory
from .retrieval import NO_RELEVANT_INFORMATION, RetrievalResult, RetrievalService
from .validation import CitationValidator, GroundingValidator, ValidatedCitation


class GenerationProviderError(RuntimeError):
    """A provider could not generate a response and fallback may continue."""


class GenerationProvider(Protocol):
    name: str
    model: str
    async def generate(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class GenerationResponse:
    content: str
    citations: list[ValidatedCitation]
    provider: str
    model: str
    cache_hit: bool
    latency_ms: float


class GeminiGenerationProvider:
    name = "gemini"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None, model: str | None = None) -> None:
        self.model = model or settings.gemini_generation_model
        self.api_key = settings.gemini_api_key
        self.base_url = settings.gemini_api_url.rstrip("/")
        self._client = client

    async def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise GenerationProviderError("Gemini generation is not configured.")
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=60)
        try:
            response = await client.post(
                f"{self.base_url}/models/{self.model}:generateContent",
                params={"key": self.api_key},
                json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
            )
            response.raise_for_status()
            payload = response.json()
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        except GenerationProviderError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise GenerationProviderError(redact_sensitive_text(f"Gemini generation failed: {exc}")) from None
        finally:
            if owns_client:
                await client.aclose()


class OpenAICompatibleProvider:
    def __init__(self, name: str, model: str, api_url: str | None, api_key: str | None, client: httpx.AsyncClient | None = None) -> None:
        self.name = name
        self.model = model
        self.api_url = api_url.rstrip("/") if api_url else None
        self.api_key = api_key
        self._client = client

    async def generate(self, prompt: str) -> str:
        if not self.api_url or not self.api_key:
            raise GenerationProviderError(f"{self.name} generation is not configured.")
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=60)
        try:
            response = await client.post(
                f"{self.api_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise GenerationProviderError(redact_sensitive_text(f"{self.name} generation failed: {exc}")) from None
        finally:
            if owns_client:
                await client.aclose()


class ProviderChain:
    def __init__(self, providers: list[GenerationProvider], on_event: Callable[[str, str, dict[str, Any]], Awaitable[None]] | None = None) -> None:
        self.providers = providers
        self.on_event = on_event

    async def generate(self, prompt: str) -> tuple[str, str, str]:
        if not self.providers:
            raise GenerationProviderError("No generation provider is configured.")
        last_error: Exception | None = None
        for provider in self.providers:
            try:
                content = await provider.generate(prompt)
                if self.on_event:
                    await self.on_event("generation_provider_selected", "info", {"provider": provider.name, "model": provider.model})
                return content, provider.name, provider.model
            except GenerationProviderError as exc:
                last_error = exc
                if self.on_event:
                    await self.on_event("generation_provider_failed", "warning", {"provider": provider.name, "model": provider.model, "error": str(exc)})
        raise GenerationProviderError(f"All generation providers failed: {last_error}")


def build_provider_chain(settings: Settings, on_event: Callable[[str, str, dict[str, Any]], Awaitable[None]] | None = None) -> ProviderChain:
    providers: list[GenerationProvider] = [
        GeminiGenerationProvider(settings),
        OpenAICompatibleProvider("groq", settings.groq_generation_model, settings.groq_api_url, settings.groq_api_key),
        OpenAICompatibleProvider("cerebras", settings.cerebras_generation_model, settings.cerebras_api_url, settings.cerebras_api_key),
        OpenAICompatibleProvider("openrouter", settings.openrouter_generation_model, settings.openrouter_api_url, settings.openrouter_api_key),
    ]
    configured = [
        provider for provider in providers
        if (isinstance(provider, GeminiGenerationProvider) and provider.api_key)
        or (isinstance(provider, OpenAICompatibleProvider) and provider.api_key)
    ]
    return ProviderChain(configured, on_event=on_event)


def build_memory_provider_chain(settings: Settings) -> ProviderChain:
    """Build the separate provider chain used by LangChain memory summarization."""
    providers: list[GenerationProvider] = [
        GeminiGenerationProvider(settings, model=settings.gemini_summary_model),
        OpenAICompatibleProvider("groq", settings.groq_generation_model, settings.groq_api_url, settings.groq_api_key),
        OpenAICompatibleProvider("cerebras", settings.cerebras_generation_model, settings.cerebras_api_url, settings.cerebras_api_key),
        OpenAICompatibleProvider("openrouter", settings.openrouter_generation_model, settings.openrouter_api_url, settings.openrouter_api_key),
    ]
    configured = [
        provider for provider in providers
        if (isinstance(provider, GeminiGenerationProvider) and provider.api_key)
        or (isinstance(provider, OpenAICompatibleProvider) and provider.api_key)
    ]
    return ProviderChain(configured)


class GenerationService:
    def __init__(self, retrieval: RetrievalService, memory: ConversationMemory, providers: ProviderChain, citation_validator: CitationValidator | None = None, grounding_validator: GroundingValidator | None = None, on_event: Callable[[str, str, dict[str, Any]], Awaitable[None]] | None = None) -> None:
        self.retrieval = retrieval
        self.memory = memory
        self.providers = providers
        self.citation_validator = citation_validator or CitationValidator()
        self.grounding_validator = grounding_validator or GroundingValidator()
        self.on_event = on_event

    async def answer(self, repo_id: UUID, session_id: UUID, query: str) -> GenerationResponse:
        retrieval = await self.retrieval.retrieve(repo_id, query)
        if not retrieval["results"]:
            if self.on_event:
                await self.on_event("generation_completed", "info", {"provider": "none", "model": "none", "latency_ms": 0.0, "retrieval_count": 0, "memory_tokens": 0})
            return GenerationResponse(NO_RELEVANT_INFORMATION, [], "none", "none", retrieval["cache_hit"], 0.0)
        results = [_result_from_dict(item) for item in retrieval["results"]]
        try:
            memory_history = await self.memory.load_history(session_id)
        except Exception as exc:
            raise GenerationProviderError(f"Conversation memory failed: {exc}") from exc
        prompt = build_prompt(query, results, memory_history)
        started = time.perf_counter()
        content, provider, model = await self.providers.generate(prompt)
        latency_ms = (time.perf_counter() - started) * 1000
        citation_result = self.citation_validator.validate(content, results)
        validation = self.grounding_validator.validate(content, citation_result, results)
        if self.on_event:
            await self.on_event("response_validation", "info", {"valid": validation.valid, "citation_count": len(validation.citations), "provider": provider, "model": model, "latency_ms": latency_ms})
        if not validation.valid:
            raise GenerationProviderError(f"Generated response failed validation: {validation.reason}")
        if self.on_event:
            await self.on_event("generation_completed", "info", {"provider": provider, "model": model, "latency_ms": latency_ms, "retrieval_count": len(results)})
        return GenerationResponse(content, validation.citations, provider, model, retrieval["cache_hit"], latency_ms)


def format_retrieved_evidence(results: list[RetrievalResult]) -> str:
    """Serialize retrieved chunks into explicit, citation-aware JSON evidence.

    RetrievalResult remains the internal contract for retrieval, reranking, and
    validation. This formatter only defines the representation sent to an LLM.
    """
    evidence = []
    for index, result in enumerate(results, start=1):
        evidence.append({
            "evidence_id": index,
            "filepath": result.filepath,
            "start_line": result.start_line,
            "end_line": result.end_line,
            "symbol": result.symbol,
            "code": result.content,
            # Preserve the remaining metadata already exposed to generation.
            "language": result.language,
            "symbol_type": result.symbol_type,
            "class_name": result.class_name,
            "parent_symbol": result.parent_symbol,
            "imports": result.imports,
        })
    return json.dumps(evidence, ensure_ascii=False, indent=2, default=str)


def build_prompt(query: str, results: list[RetrievalResult], memory_history: str) -> str:
    evidence = format_retrieved_evidence(results)
    return (
        "You are Code Atlas, a repository code intelligence assistant. Return Markdown.\n\n"
        "GROUNDING RULES:\n"
        "- Answer ONLY from RETRIEVED EVIDENCE. Do not use outside knowledge.\n"
        "- Do not invent files, functions, classes, variables, behavior, dependencies, or relationships.\n"
        "- MEMORY SUMMARY and RECENT TURNS inside CONVERSATIONAL MEMORY are context only, NOT repository evidence.\n"
        "- If the evidence is insufficient, explicitly say that the available evidence is insufficient instead of guessing.\n\n"
        "CITATION RULES:\n"
        "- Every substantive repository-related claim must have a citation immediately after the claim it supports.\n"
        "- Use filepath:start_line-end_line. If symbol is not null, use filepath:start_line-end_line (symbol_name).\n"
        "- Use only filepath, start_line, end_line, and symbol supplied by RETRIEVED EVIDENCE. Never invent or estimate line numbers.\n"
        "- Cite the smallest relevant line range that supports the claim.\n"
        "- Do not attach a citation to a claim that the cited lines do not support.\n"
        "- If a claim requires multiple evidence items, cite each relevant item.\n"
        "- Do not create a separate Sources section unless requested.\n\n"
        f"CURRENT QUERY:\n{query}\n\n"
        f"CONVERSATIONAL MEMORY (MEMORY SUMMARY + RECENT TURNS):\n{memory_history or '(none)'}\n\n"
        f"RETRIEVED EVIDENCE:\n{evidence}"
    )


def _result_from_dict(value: dict[str, Any]) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=value["chunk_id"], repo_id=value["repo_id"], content=value["content"], filepath=value["filepath"],
        language=value.get("language"), symbol=value.get("symbol"), symbol_type=value.get("symbol_type"),
        class_name=value.get("class_name"), parent_symbol=value.get("parent_symbol"), start_line=value.get("start_line"),
        end_line=value.get("end_line"), imports=value.get("imports") or [], dense_score=value.get("dense_score"),
        dense_rank=value.get("dense_rank"), sparse_score=value.get("sparse_score"), sparse_rank=value.get("sparse_rank"),
        rrf_score=value.get("rrf_score"), rrf_rank=value.get("rrf_rank"), reranker_score=value.get("reranker_score"),
        reranker_rank=value.get("reranker_rank"),
    )
