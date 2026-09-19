import asyncio
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol
from uuid import UUID

NO_RELEVANT_INFORMATION = "I couldn't find relevant information in this project."
DENSE_TOP_K = 20
SPARSE_TOP_K = 20
RRF_TOP_K = 15
FINAL_TOP_K = 5


@dataclass
class RetrievalResult:
    chunk_id: UUID | str
    repo_id: UUID | str
    content: str
    filepath: str
    language: str | None = None
    symbol: str | None = None
    symbol_type: str | None = None
    class_name: str | None = None
    parent_symbol: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    imports: list[str] = field(default_factory=list)
    dense_score: float | None = None
    dense_rank: int | None = None
    sparse_score: float | None = None
    sparse_rank: int | None = None
    rrf_score: float | None = None
    rrf_rank: int | None = None
    reranker_score: float | None = None
    reranker_rank: int | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["chunk_id"] = str(self.chunk_id)
        value["repo_id"] = str(self.repo_id)
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RetrievalResult":
        return cls(
            chunk_id=value["chunk_id"],
            repo_id=value["repo_id"],
            content=value["content"],
            filepath=value["filepath"],
            language=value.get("language"),
            symbol=value.get("symbol"),
            symbol_type=value.get("symbol_type"),
            class_name=value.get("class_name"),
            parent_symbol=value.get("parent_symbol"),
            start_line=value.get("start_line"),
            end_line=value.get("end_line"),
            imports=value.get("imports") or [],
            dense_score=value.get("dense_score"),
            dense_rank=value.get("dense_rank"),
            sparse_score=value.get("sparse_score"),
            sparse_rank=value.get("sparse_rank"),
            rrf_score=value.get("rrf_score"),
            rrf_rank=value.get("rrf_rank"),
            reranker_score=value.get("reranker_score"),
            reranker_rank=value.get("reranker_rank"),
        )

    @classmethod
    def from_row(cls, row: dict[str, Any], repo_id: UUID | str) -> "RetrievalResult":
        metadata = row.get("chunk_metadata") or row.get("metadata") or row
        chunk_id = row.get("id") or row.get("chunk_id")
        if chunk_id is None:
            raise RetrievalError("Retrieval row is missing chunk ID.")
        return cls(
            chunk_id=chunk_id,
            repo_id=repo_id,
            content=row.get("content", ""),
            filepath=metadata.get("filepath", ""),
            language=metadata.get("language"),
            symbol=metadata.get("symbol"),
            symbol_type=metadata.get("symbol_type"),
            class_name=metadata.get("class_name"),
            parent_symbol=metadata.get("parent_symbol"),
            start_line=metadata.get("start_line"),
            end_line=metadata.get("end_line"),
            imports=metadata.get("imports") or [],
            dense_score=row.get("similarity"),
            sparse_score=row.get("rank_score") or row.get("ts_rank"),
        )



class CacheError(RuntimeError):
    """Semantic cache storage failed."""


class RetrievalError(RuntimeError):
    """A retrieval or reranking stage failed."""


class RetrieverPersistence(Protocol):
    async def get_semantic_cache(self, repo_id: UUID, query_embedding: list[float], threshold: float) -> dict[str, Any] | None: ...
    async def save_semantic_cache(self, repo_id: UUID, query: str, query_embedding: list[float], response: dict[str, Any]) -> None: ...
    async def dense_search(self, repo_id: UUID, query_embedding: list[float], limit: int) -> list[dict[str, Any]]: ...
    async def sparse_search(self, repo_id: UUID, query: str, limit: int) -> list[dict[str, Any]]: ...


class Reranker(Protocol):
    async def rerank(self, query: str, candidates: list[RetrievalResult], limit: int) -> list[RetrievalResult]: ...


def reciprocal_rank_fusion(dense: list[RetrievalResult], sparse: list[RetrievalResult], limit: int = RRF_TOP_K, k: int = 60) -> list[RetrievalResult]:
    merged: dict[str, RetrievalResult] = {}
    scores: dict[str, float] = {}
    for rank, result in enumerate(dense, start=1):
        key = str(result.chunk_id)
        merged.setdefault(key, result)
        merged[key].dense_rank = rank
        merged[key].dense_score = result.dense_score
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    for rank, result in enumerate(sparse, start=1):
        key = str(result.chunk_id)
        merged.setdefault(key, result)
        merged[key].sparse_rank = rank
        merged[key].sparse_score = result.sparse_score
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    ordered = sorted(merged, key=lambda key: (-scores[key], key))[:limit]
    results = []
    for rank, key in enumerate(ordered, start=1):
        result = merged[key]
        result.rrf_score = scores[key]
        result.rrf_rank = rank
        results.append(result)
    return results


class RetrievalService:
    def __init__(self, persistence: RetrieverPersistence, embedder: Any, reranker: Reranker, cache_threshold: float = 0.92) -> None:
        self.persistence = persistence
        self.embedder = embedder
        self.reranker = reranker
        self.cache_threshold = cache_threshold

    async def retrieve(self, repo_id: UUID, query: str, allow_cache_hit: bool = True) -> dict[str, Any]:
        if not query.strip():
            return {"query": query, "repo_id": repo_id, "cache_hit": False, "results": [], "message": NO_RELEVANT_INFORMATION, "latency_ms": {}}
        total_start = time.perf_counter()
        embedding_start = time.perf_counter()
        try:
            query_embedding = (await self.embedder.embed_documents([query]))[0]
        except Exception as exc:
            raise RetrievalError(f"Query embedding failed: {exc}") from exc
        embedding_ms = (time.perf_counter() - embedding_start) * 1000
        cache_start = time.perf_counter()
        try:
            cached = await self.persistence.get_semantic_cache(repo_id, query_embedding, self.cache_threshold)
        except Exception as exc:
            raise CacheError(f"Semantic cache lookup failed: {exc}") from exc
        cache_ms = (time.perf_counter() - cache_start) * 1000
        if cached is not None and allow_cache_hit:
            return {**cached, "query": query, "repo_id": repo_id, "cache_hit": True, "latency_ms": {"query_embedding": embedding_ms, "cache": cache_ms, "total": (time.perf_counter() - total_start) * 1000}}

        async def timed(operation: Any) -> tuple[Any, float]:
            started = time.perf_counter()
            value = await operation
            return value, (time.perf_counter() - started) * 1000

        try:
            (dense, dense_ms), (sparse, sparse_ms) = await asyncio.gather(
                timed(self.persistence.dense_search(repo_id, query_embedding, DENSE_TOP_K)),
                timed(self.persistence.sparse_search(repo_id, query, SPARSE_TOP_K)),
            )
        except Exception as exc:
            raise RetrievalError(f"Candidate retrieval failed: {exc}") from exc
        dense_results = [RetrievalResult.from_row(row, repo_id) for row in dense[:DENSE_TOP_K]]
        sparse_results = [RetrievalResult.from_row(row, repo_id) for row in sparse[:SPARSE_TOP_K]]
        fusion_start = time.perf_counter()
        fused = reciprocal_rank_fusion(dense_results, sparse_results, RRF_TOP_K)
        fusion_ms = (time.perf_counter() - fusion_start) * 1000
        rerank_start = time.perf_counter()
        try:
            final_results = await self.reranker.rerank(query, fused, FINAL_TOP_K)
        except Exception as exc:
            raise RetrievalError(f"Cross-encoder reranking failed: {exc}") from exc
        rerank_ms = (time.perf_counter() - rerank_start) * 1000
        payload = {
            "results": [result.to_dict() for result in final_results[:FINAL_TOP_K]],
            "message": None if final_results else NO_RELEVANT_INFORMATION,
            "retrieval_candidates": len(fused),
            "dense_count": len(dense_results),
            "sparse_count": len(sparse_results),
            "reranked_count": len(final_results),
            "latency_ms": {"query_embedding": embedding_ms, "cache": cache_ms, "dense": dense_ms, "sparse": sparse_ms, "fusion": fusion_ms, "reranking": rerank_ms, "total": (time.perf_counter() - total_start) * 1000},
        }
        if allow_cache_hit:
            try:
                await self.persistence.save_semantic_cache(repo_id, query, query_embedding, payload)
            except Exception as exc:
                raise CacheError(f"Semantic cache write failed: {exc}") from exc
        return {**payload, "query": query, "repo_id": repo_id, "cache_hit": False}
