import os
from uuid import uuid4
import pytest

from app.config import Settings
from app.services.observability import (
    create_runnable_config,
    flush_langsmith_traces,
    safe_traceable,
    setup_langsmith_environment,
)
from app.services.generation import GenerationService, ProviderChain
from app.services.memory import ConversationMemory, ProviderChainLanguageModel
from app.services.retrieval import RetrievalResult, RetrievalService


class FakeProvider:
    def __init__(self, name="gemini", content=None):
        self.name = name
        self.model = f"{name}-model"
        self.content = content or "The run function returns 42. `src/run.py:1-1 run`"

    async def generate(self, prompt):
        return self.content

    async def generate_stream(self, prompt):
        for token in ["The ", "run ", "function ", "returns ", "42. ", "`src/run.py:1-1 run`"]:
            yield token


class FakeMessageStore:
    def __init__(self, messages=None):
        self.messages = messages or {}

    async def get_messages(self, session_id):
        return self.messages.get(session_id, [])


class FakeSummaryChain:
    async def generate(self, prompt):
        return "Summary of earlier discussion.", "fake", "fake-model"


class FakeStore:
    def __init__(self):
        self.cache = None

    async def get_semantic_cache(self, repo_id, query_embedding, threshold):
        return self.cache

    async def save_semantic_cache(self, repo_id, query, query_embedding, payload):
        self.cache = payload

    async def dense_search(self, repo_id, query_embedding, limit):
        return [{
            "id": "chunk-1",
            "similarity": 0.95,
            "content": "def run(): return 42",
            "filepath": "src/run.py",
            "symbol": "run",
            "symbol_type": "function_definition",
            "start_line": 1,
            "end_line": 1,
        }]

    async def sparse_search(self, repo_id, query, limit):
        return [{
            "id": "chunk-1",
            "rank_score": 10.0,
            "content": "def run(): return 42",
            "filepath": "src/run.py",
            "symbol": "run",
            "symbol_type": "function_definition",
            "start_line": 1,
            "end_line": 1,
        }]


class FakeEmbedder:
    async def embed_documents(self, texts):
        return [[0.1] * 768 for _ in texts]


class FakeReranker:
    async def rerank(self, query, candidates, limit):
        return candidates[:limit]


def test_setup_langsmith_environment_when_disabled():
    settings = Settings(langsmith_tracing=False, langsmith_api_key=None)
    result = setup_langsmith_environment(settings)
    assert result is False


def test_setup_langsmith_environment_when_enabled(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)

    settings = Settings(
        langsmith_tracing=True,
        langsmith_api_key="lsv2_pt_testkey123",
        langsmith_project="test-project",
        langsmith_endpoint="https://api.smith.langchain.com",
    )
    result = setup_langsmith_environment(settings)

    assert result is True
    assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
    assert os.environ.get("LANGCHAIN_API_KEY") == "lsv2_pt_testkey123"
    assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"


def test_create_runnable_config_isolation_and_redaction():
    settings = Settings(langsmith_tracing=False, langsmith_environment="test")
    config = create_runnable_config(
        tags=["chat", "test"],
        metadata={"repo_id": "123", "secret_token": "Bearer secret12345"},
        settings=settings,
    )

    assert "chat" in config["tags"]
    assert "env:test" in config["tags"]
    assert config["metadata"]["repo_id"] == "123"
    # Redaction verification
    assert "Bearer [REDACTED]" in config["metadata"]["secret_token"]


def test_flush_langsmith_traces_does_not_raise():
    # Should complete safely without exception
    flush_langsmith_traces()


@pytest.mark.asyncio
async def test_safe_traceable_decorator():
    @safe_traceable(name="test_task", tags=["test"])
    async def sample_task(x: int, y: int) -> int:
        return x + y

    result = await sample_task(3, 4)
    assert result == 7


@pytest.mark.asyncio
async def test_retrieval_and_generation_with_runnable_config():
    store = FakeStore()
    retrieval = RetrievalService(store, FakeEmbedder(), FakeReranker())
    repo_id = uuid4()
    session_id = uuid4()

    config = create_runnable_config(
        tags=["chat", "integration"],
        metadata={"repo_id": str(repo_id), "session_id": str(session_id)},
    )

    retrieval_res = await retrieval.retrieve(repo_id, "What does run do?", config=config)
    assert len(retrieval_res["results"]) == 1

    memory = ConversationMemory(FakeMessageStore(), ProviderChainLanguageModel(provider_chain=FakeSummaryChain()))
    service = GenerationService(
        retrieval=retrieval,
        memory=memory,
        providers=ProviderChain([FakeProvider()]),
    )

    # Test complete answer with config
    response = await service.answer(repo_id, session_id, "What does run do?", config=config)
    assert response.provider == "gemini"
    assert len(response.citations) >= 1
    assert response.citations[0].filepath == "src/run.py"

    # Test streaming answer with config
    chunks = []
    async for item in service.answer_stream(repo_id, session_id, "What does run do?", config=config):
        chunks.append(item)

    token_chunks = [c for c in chunks if c["type"] == "token"]
    done_chunks = [c for c in chunks if c["type"] == "done"]

    assert len(token_chunks) > 0
    assert len(done_chunks) == 1
    assert done_chunks[0]["citations"][0]["file"] == "src/run.py"


@pytest.mark.asyncio
async def test_generation_error_captured_by_chain():
    class FailingProvider:
        name = "failing"
        model = "fail-model"
        async def generate(self, prompt):
            from app.services.generation import GenerationProviderError
            raise GenerationProviderError("Rate limit reached")
        async def generate_stream(self, prompt):
            from app.services.generation import GenerationProviderError
            raise GenerationProviderError("Rate limit reached")
            yield ""

    store = FakeStore()
    retrieval = RetrievalService(store, FakeEmbedder(), FakeReranker())
    repo_id = uuid4()
    session_id = uuid4()

    memory = ConversationMemory(FakeMessageStore(), ProviderChainLanguageModel(provider_chain=FakeSummaryChain()))
    service = GenerationService(
        retrieval=retrieval,
        memory=memory,
        providers=ProviderChain([FailingProvider()]),
    )

    from app.services.generation import GenerationProviderError
    with pytest.raises(GenerationProviderError, match="Rate limit reached"):
        await service.answer(repo_id, session_id, "What does run do?")

    with pytest.raises(GenerationProviderError, match="Rate limit reached"):
        async for _ in service.answer_stream(repo_id, session_id, "What does run do?"):
            pass

