import pytest

from app.services.reranking import CrossEncoderReranker
from app.services.retrieval import RetrievalResult


class FakeLangChainCrossEncoder:
    def __init__(self):
        self.pairs = None

    def score(self, pairs):
        self.pairs = pairs
        return [0.2, 0.9, 0.4]


@pytest.mark.asyncio
async def test_langchain_cross_encoder_wrapper_scores_candidates_and_returns_limit():
    model = FakeLangChainCrossEncoder()
    reranker = CrossEncoderReranker("cross-encoder/test", model=model)
    candidates = [
        RetrievalResult(chunk_id=str(index), repo_id="repo", content=f"content {index}", filepath="file.py")
        for index in range(3)
    ]

    results = await reranker.rerank("query", candidates, limit=2)

    assert model.pairs == [("query", "content 0"), ("query", "content 1"), ("query", "content 2")]
    assert [result.chunk_id for result in results] == ["1", "2"]
    assert len(results) == 2
    assert results[0].reranker_rank == 1
    assert results[0].reranker_score == 0.9