from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest

from app.database.repositories import DatabaseRepository
from app.embeddings.embedding_service import EmbeddingService
from app.retrieval.bm25_index import BM25Registry, tokenize
from app.retrieval.step_01_query_preprocessor import QueryPreprocessor
from app.retrieval.step_02_semantic_cache import SemanticCache
from app.retrieval.step_04_rrf_fusion import RRFFusion
from app.retrieval.step_05_reranker import CrossEncoderReranker
from app.schemas.retrieval import ChunkRecord, RetrievalResult


def test_bm25_registry():
    assert tokenize("def calculate_sum(x, y):") == ["def", "calculate_sum", "x", "y"]
    registry = BM25Registry()
    repo_id = uuid4()
    c1 = ChunkRecord(content_hash="h1", content="def calculate_total(): pass", filepath="math.py")
    c2 = ChunkRecord(content_hash="h2", content="def render_view(): pass", filepath="view.py")

    registry.register(repo_id, [c1, c2])
    assert registry.has_index(repo_id) is True

    hits = registry.query(repo_id, "calculate total", top_k=2)
    assert len(hits) >= 1
    assert hits[0][0].filepath == "math.py"


@pytest.mark.asyncio
async def test_query_preprocessor():
    mock_embedder = MagicMock(spec=EmbeddingService)
    mock_embedder.embed_documents = AsyncMock(return_value=[[0.05] * 768])
    prep = QueryPreprocessor(embedder=mock_embedder)

    clean, emb = await prep.preprocess("  find   router   \x00")
    assert clean == "find router"
    assert len(emb) == 768


def test_rrf_fusion():
    c_a = ChunkRecord(chunk_id=uuid4(), content_hash="a", content="A", filepath="a.py")
    c_b = ChunkRecord(chunk_id=uuid4(), content_hash="b", content="B", filepath="b.py")
    c_c = ChunkRecord(chunk_id=uuid4(), content_hash="c", content="C", filepath="c.py")

    dense = [RetrievalResult(chunk=c_a, score=0.9), RetrievalResult(chunk=c_b, score=0.8)]
    sparse = [RetrievalResult(chunk=c_b, score=5.0), RetrievalResult(chunk=c_c, score=4.0)]

    fuser = RRFFusion(k=60)
    fused = fuser.fuse(dense, sparse, top_k=3)

    # c_b is present in both dense and sparse, so it should rank highest!
    assert fused[0].chunk.content_hash == "b"
    assert len(fused) == 3


def test_cross_encoder_reranker_fallback():
    reranker = CrossEncoderReranker()
    c = ChunkRecord(content_hash="a", content="A", filepath="a.py")
    candidates = [RetrievalResult(chunk=c, score=0.5)]
    results = reranker.rerank("query", candidates, top_k=1)
    assert len(results) == 1
