import hashlib
from typing import Any
from uuid import UUID

from app.database.connection import DatabaseConnection, get_db_connection


class DatabaseRepository:
    """Unified data access layer for repositories, chunks, semantic cache, and RPCs."""

    def __init__(self, connection: DatabaseConnection | None = None) -> None:
        self.conn = connection or get_db_connection()

    async def get_repo(self, repo_id: UUID) -> dict[str, Any] | None:
        rows = await self.conn.execute("GET", f"repos?id=eq.{repo_id}&limit=1")
        return rows[0] if rows else None

    async def list_repos(self) -> list[dict[str, Any]]:
        return await self.conn.execute("GET", "repos?order=updated_at.desc") or []

    async def upsert_repo(self, payload: dict[str, Any]) -> None:
        headers = {"Prefer": "resolution=merge-duplicates"}
        await self.conn.execute("POST", "repos?on_conflict=id", json=[payload], headers=headers)

    async def update_repo_status(self, repo_id: UUID, status: str, error: str | None = None) -> None:
        await self.conn.execute("PATCH", f"repos?id=eq.{repo_id}", json={"status": status, "error": error})

    async def get_chunks_by_hashes(self, repo_id: UUID, hashes: list[str]) -> list[dict[str, Any]]:
        if not hashes:
            return []
        val_str = ",".join(hashes)
        return await self.conn.execute("GET", f"chunks?repo_id=eq.{repo_id}&content_hash=in.({val_str})&select=*,chunk_metadata(*)") or []

    async def upsert_chunks(self, chunks: list[dict[str, Any]], metadata: list[dict[str, Any]]) -> None:
        if not chunks:
            return
        headers = {"Prefer": "resolution=merge-duplicates"}
        await self.conn.execute("POST", "chunks?on_conflict=repo_id,content_hash", json=chunks, headers=headers)
        if metadata:
            await self.conn.execute("POST", "chunk_metadata?on_conflict=chunk_id", json=metadata, headers=headers)

    async def dense_search(self, repo_id: UUID, query_embedding: list[float], limit: int = 20) -> list[dict[str, Any]]:
        payload = {"match_repo_id": str(repo_id), "query_embedding": query_embedding, "match_count": limit}
        return await self.conn.execute("POST", "rpc/match_chunks", json=payload) or []

    async def sparse_search(self, repo_id: UUID, query_text: str, limit: int = 20) -> list[dict[str, Any]]:
        payload = {"match_repo_id": str(repo_id), "search_query": query_text, "match_count": limit}
        return await self.conn.execute("POST", "rpc/search_chunks", json=payload) or []

    async def get_semantic_cache(self, repo_id: UUID, query_embedding: list[float], threshold: float = 0.92) -> dict[str, Any] | None:
        payload = {"p_repo_id": str(repo_id), "p_query_embedding": query_embedding, "p_similarity_threshold": threshold}
        rows = await self.conn.execute("POST", "rpc/match_semantic_cache", json=payload)
        return rows[0]["response"] if rows else None

    async def save_semantic_cache(self, repo_id: UUID, query: str, query_embedding: list[float], response: dict[str, Any]) -> None:
        q_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
        payload = [{"repo_id": str(repo_id), "query_hash": q_hash, "query_text": query, "query_embedding": query_embedding, "response": response}]
        headers = {"Prefer": "resolution=merge-duplicates"}
        await self.conn.execute("POST", "semantic_cache?on_conflict=repo_id,query_hash", json=payload, headers=headers)
