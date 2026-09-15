import asyncio
from uuid import uuid4

import pytest

from app.services.retrieval import RetrievalError, RetrievalService


class FakeEmbedder:
    async def embed_documents(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


class FakeReranker:
    def __init__(self):
        self.received = []

    async def rerank(self, query, candidates, limit):
        self.received.append((query, len(candidates), limit))
        for rank, candidate in enumerate(reversed(candidates[:limit]), start=1):
            candidate.reranker_rank = rank
            candidate.reranker_score = float(rank)
        return list(reversed(candidates[:limit]))


class FailingReranker:
    async def rerank(self, query, candidates, limit):
        raise RuntimeError("reranker unavailable")


class FakePersistence:
    def __init__(self):
        self.cache = {}
        self.saved = []
        self.dense_calls = []
        self.sparse_calls = []

    async def get_semantic_cache(self, repo_id, query_embedding, threshold):
        return self.cache.get(repo_id)

    async def save_semantic_cache(self, repo_id, query, query_embedding, response):
        self.cache[repo_id] = response
        self.saved.append((repo_id, query))

    async def dense_search(self, repo_id, query_embedding, limit):
        self.dense_calls.append((repo_id, limit))
        await asyncio.sleep(0.01)
        return [{"id": f"dense-{index}", "content": f"dense {index}", "filepath": "a.py", "symbol": "run", "similarity": 1.0 - index / 100} for index in range(20)]

    async def sparse_search(self, repo_id, query, limit):
        self.sparse_calls.append((repo_id, query, limit))
        await asyncio.sleep(0.01)
        return [{"id": f"sparse-{index}", "content": f"sparse {index}", "filepath": "b.py", "symbol": "authenticateUser", "rank_score": 20 - index} for index in range(20)]


@pytest.mark.asyncio
async def test_retrieval_runs_parallel_candidates_and_limits_reranking():
    persistence = FakePersistence()
    reranker = FakeReranker()
    service = RetrievalService(persistence, FakeEmbedder(), reranker)
    result = await service.retrieve(uuid4(), "authenticateUser")

    assert result["cache_hit"] is False
    assert result["retrieval_candidates"] == 15
    assert len(result["results"]) == 5
    assert reranker.received == [("authenticateUser", 15, 5)]
    assert persistence.dense_calls[0][1] == 20
    assert persistence.sparse_calls[0][2] == 20
    assert result["latency_ms"]["dense"] >= 0
    assert result["latency_ms"]["sparse"] >= 0


@pytest.mark.asyncio
async def test_cache_is_repo_scoped_and_second_query_hits():
    persistence = FakePersistence()
    service = RetrievalService(persistence, FakeEmbedder(), FakeReranker())
    repo_a = uuid4()
    repo_b = uuid4()

    first = await service.retrieve(repo_a, "same query")
    second = await service.retrieve(repo_a, "equivalent query")
    other_repo = await service.retrieve(repo_b, "same query")

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert other_repo["cache_hit"] is False
    assert [item[0] for item in persistence.saved] == [repo_a, repo_b]


@pytest.mark.asyncio
async def test_evaluation_retrieval_can_bypass_cached_payload_without_writing_cache():
    persistence = FakePersistence()
    service = RetrievalService(persistence, FakeEmbedder(), FakeReranker())
    repo_id = uuid4()

    await service.retrieve(repo_id, "first query")
    result = await service.retrieve(repo_id, "evaluation query", allow_cache_hit=False)

    assert result["cache_hit"] is False
    assert len(persistence.dense_calls) == 2
    assert len(persistence.sparse_calls) == 2
    assert [item[0] for item in persistence.saved] == [repo_id]


@pytest.mark.asyncio
async def test_reranker_failure_is_explicit():
    service = RetrievalService(FakePersistence(), FakeEmbedder(), FailingReranker())
    with pytest.raises(RetrievalError, match="reranking failed"):
        await service.retrieve(uuid4(), "query")


@pytest.mark.asyncio
async def test_empty_candidates_return_architecture_message():
    persistence = FakePersistence()
    persistence.dense_search = lambda repo_id, query_embedding, limit: _empty()
    persistence.sparse_search = lambda repo_id, query, limit: _empty()
    service = RetrievalService(persistence, FakeEmbedder(), FakeReranker())
    result = await service.retrieve(uuid4(), "query")
    assert result["results"] == []
    assert result["message"] == "I couldn't find relevant information in this project."


async def _empty():
    return []
