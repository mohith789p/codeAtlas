import asyncio
import logging
from typing import Any
from uuid import UUID

from app.database.repositories import DatabaseRepository
from app.retrieval.bm25_index import get_bm25_registry
from app.schemas.retrieval import ChunkRecord, RetrievalResult

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Concurrently queries PostgreSQL dense HNSW vector search and BM25 sparse search."""

    def __init__(self, db_repo: DatabaseRepository | None = None) -> None:
        self.db_repo = db_repo or DatabaseRepository()
        self.bm25_registry = get_bm25_registry()

    async def retrieve(
        self, repo_id: UUID, query_text: str, query_embedding: list[float], limit: int = 20
    ) -> tuple[list[RetrievalResult], list[RetrievalResult]]:
        """Concurrently fetch top dense candidates and top BM25 sparse candidates."""
        dense_task = self._dense_search(repo_id, query_embedding, limit)
        sparse_task = self._sparse_search(repo_id, query_text, limit)
        dense_res, sparse_res = await asyncio.gather(dense_task, sparse_task)
        return dense_res, sparse_res

    async def _dense_search(self, repo_id: UUID, query_embedding: list[float], limit: int) -> list[RetrievalResult]:
        try:
            rows = await self.db_repo.dense_search(repo_id, query_embedding, limit)
            results: list[RetrievalResult] = []
            for r in rows:
                c = ChunkRecord(
                    chunk_id=r["id"], content_hash="", content=r["content"],
                    filepath=r["filepath"], language=r.get("language"),
                    symbol=r.get("symbol"), symbol_type=r.get("symbol_type"),
                    class_name=r.get("class_name"), parent_symbol=r.get("parent_symbol"),
                    start_line=r.get("start_line"), end_line=r.get("end_line"),
                    imports=r.get("imports") or [],
                )
                results.append(RetrievalResult(chunk=c, score=float(r.get("similarity", 0.0)), dense_score=float(r.get("similarity", 0.0))))
            return results
        except Exception as exc:
            logger.error("Dense HNSW search failed for repo %s: %s", repo_id, exc)
            return []

    async def _sparse_search(self, repo_id: UUID, query_text: str, limit: int) -> list[RetrievalResult]:
        # Priority 1: Hot in-memory BM25 registry
        if self.bm25_registry.has_index(repo_id):
            bm25_matches = self.bm25_registry.query(repo_id, query_text, top_k=limit)
            return [RetrievalResult(chunk=c, score=s, sparse_score=s) for c, s in bm25_matches]

        # Priority 2: Fallback to Postgres search_chunks RPC
        try:
            rows = await self.db_repo.sparse_search(repo_id, query_text, limit)
            results: list[RetrievalResult] = []
            for r in rows:
                c = ChunkRecord(
                    chunk_id=r["id"], content_hash="", content=r["content"],
                    filepath=r["filepath"], language=r.get("language"),
                    symbol=r.get("symbol"), symbol_type=r.get("symbol_type"),
                    start_line=r.get("start_line"), end_line=r.get("end_line"),
                )
                results.append(RetrievalResult(chunk=c, score=float(r.get("rank_score", 0.0)), sparse_score=float(r.get("rank_score", 0.0))))
            return results
        except Exception as exc:
            logger.error("Sparse search failed for repo %s: %s", repo_id, exc)
            return []
