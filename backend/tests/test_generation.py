import json
from uuid import uuid4

import httpx
import pytest

from app.config import Settings
from app.services.generation import (
    GenerationProviderError,
    GeminiGenerationProvider,
    GenerationService,
    OpenAICompatibleProvider,
    ProviderChain,
    build_prompt,
    format_retrieved_evidence,
)
from app.services.memory import ConversationMemory, ProviderChainLanguageModel
from app.services.retrieval import RetrievalResult


class FakeProvider:
    def __init__(self, name, content=None, fail=False):
        self.name = name
        self.model = f"{name}-model"
        self.content = content
        self.fail = fail
        self.calls = 0

    async def generate(self, prompt):
        self.calls += 1
        if self.fail:
            raise GenerationProviderError(f"{self.name} unavailable")
        return self.content or "ok"


class FakeMessageStore:
    def __init__(self, messages=None):
        self.messages = messages or {}

    async def get_messages(self, session_id):
        return self.messages.get(session_id, [])


class FakeRetrieval:
    def __init__(self, result):
        self.result = result

    async def retrieve(self, repo_id, query):
        return self.result


class FakeSummaryChain:
    async def generate(self, prompt):
        return "Summary of earlier repository discussion.", "fake", "fake-model"


class FakeReranker:
    async def rerank(self, query, candidates, limit):
        return candidates[:limit]


def retrieved_payload():
    result = RetrievalResult(
        chunk_id="chunk-1", repo_id="repo-1", content="def run(): return 42", filepath="src/run.py",
        language="python", symbol="run", symbol_type="function_definition", start_line=1, end_line=1,
    )
    return {"results": [result.to_dict()], "cache_hit": False}


def test_format_retrieved_evidence_preserves_citation_metadata_and_distinguishes_chunks():
    results = [
        RetrievalResult(
            chunk_id="chunk-1", repo_id="repo-1", content="async def get_repository(): pass",
            filepath="src/api/repositories.py", symbol="get_repository", start_line=42, end_line=44,
        ),
        RetrievalResult(
            chunk_id="chunk-2", repo_id="repo-1", content="return await repo.find_by_id(repo_id)",
            filepath="src/services/repository_service.py", symbol=None, start_line=18, end_line=19,
        ),
    ]

    evidence = json.loads(format_retrieved_evidence(results))

    assert evidence == [
        {
            "evidence_id": 1,
            "filepath": "src/api/repositories.py",
            "start_line": 42,
            "end_line": 44,
            "symbol": "get_repository",
            "code": "async def get_repository(): pass",
            "language": None,
            "symbol_type": None,
            "class_name": None,
            "parent_symbol": None,
            "imports": [],
        },
        {
            "evidence_id": 2,
            "filepath": "src/services/repository_service.py",
            "start_line": 18,
            "end_line": 19,
            "symbol": None,
            "code": "return await repo.find_by_id(repo_id)",
            "language": None,
            "symbol_type": None,
            "class_name": None,
            "parent_symbol": None,
            "imports": [],
        },
    ]


def test_build_prompt_exposes_citation_metadata_and_grounding_rules():
    result = RetrievalResult(
        chunk_id="chunk-1", repo_id="repo-1", content="def run(): return 42",
        filepath="src/run.py", symbol="run", start_line=7, end_line=7,
    )

    prompt = build_prompt("What does run do?", [result], "(none)")

    assert '"filepath": "src/run.py"' in prompt
    assert '"start_line": 7' in prompt
    assert '"end_line": 7' in prompt
    assert '"symbol": "run"' in prompt
    assert '"code": "def run(): return 42"' in prompt
    assert "Answer ONLY from RETRIEVED EVIDENCE" in prompt
    assert "MEMORY SUMMARY and RECENT TURNS inside CONVERSATIONAL MEMORY are context only, NOT repository evidence" in prompt
    assert "Do not create a separate Sources section unless requested" in prompt


@pytest.mark.asyncio
async def test_provider_chain_falls_back_and_logs_provider_failure():
    events = []

    async def on_event(stage, level, metadata):
        events.append((stage, level, metadata))

    first = FakeProvider("gemini", fail=True)
    second = FakeProvider("groq", content="answer")
    response = await ProviderChain([first, second], on_event).generate("prompt")

    assert response == ("answer", "groq", "groq-model")
    assert [event[0] for event in events] == ["generation_provider_failed", "generation_provider_selected"]


@pytest.mark.asyncio
async def test_provider_chain_rejects_no_configured_providers():
    with pytest.raises(GenerationProviderError, match="No generation provider"):
        await ProviderChain([]).generate("prompt")


@pytest.mark.asyncio
async def test_generation_returns_markdown_and_validated_citation():
    session_id = uuid4()
    provider = FakeProvider("gemini", "The run function returns 42. `src/run.py:1-1 run`")
    service = GenerationService(
        FakeRetrieval(retrieved_payload()),
        ConversationMemory(FakeMessageStore(), ProviderChainLanguageModel(provider_chain=FakeSummaryChain())),
        ProviderChain([provider]),
    )

    response = await service.answer(uuid4(), session_id, "What does run do?")

    assert response.provider == "gemini"
    assert response.citations[0].filepath == "src/run.py"
    assert response.citations[0].symbol == "run"


@pytest.mark.asyncio
async def test_generation_with_no_retrieved_results_returns_architecture_message():
    events = []

    async def on_event(stage, level, metadata):
        events.append(stage)

    service = GenerationService(
        FakeRetrieval({"results": [], "cache_hit": False}),
        ConversationMemory(FakeMessageStore(), ProviderChainLanguageModel(provider_chain=FakeSummaryChain())),
        ProviderChain([FakeProvider("gemini", "unused")]),
        on_event=on_event,
    )

    response = await service.answer(uuid4(), uuid4(), "unknown")

    assert response.content == "I couldn't find relevant information in this project."
    assert response.provider == "none"
    assert "generation_completed" in events


@pytest.mark.asyncio
async def test_gemini_generation_provider_parses_realistic_response_shape():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "answer"}]}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GeminiGenerationProvider(Settings(gemini_api_key="key"), client)
    assert await provider.generate("prompt") == "answer"
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_provider_parses_response_shape():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "answer"}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider("groq", "model", "https://example.test/v1", "key", client)
    assert await provider.generate("prompt") == "answer"
    await client.aclose()
