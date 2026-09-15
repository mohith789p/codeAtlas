import json
import hashlib
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx

from .config import Settings
from .logging_utils import redact_sensitive
from .models import ChatMessage, ChatSession, ProcessingStats, Repository, RepositoryMetadata, RepositoryStats, canonical_repository_identity
from .services.indexing import ChunkRecord


class PersistenceError(RuntimeError):
    """A durable storage operation failed."""


class SupabasePersistence:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError("Supabase URL and service-role key are required.")
        configured_url = settings.supabase_url.rstrip("/")
        self.base_url = configured_url if configured_url.endswith("/rest/v1") else configured_url + "/rest/v1"
        self.headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        self._client = client

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)
        try:
            request_headers = {**self.headers, **kwargs.pop("headers", {})}
            response = await client.request(method, f"{self.base_url}/{path}", headers=request_headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else None
        except (httpx.HTTPError, ValueError) as exc:
            raise PersistenceError(f"Supabase {method} {path} failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    async def upsert_repository(self, repository: Repository) -> None:
        payload = {
            "id": str(repository.id), "name": repository.name, "full_name": repository.full_name,
            "description": repository.description, "owner": repository.owner, "branch": repository.branch,
            "language": repository.language, "url": repository.url, "status": repository.status.value,
            "repository_key": repository.repository_key or canonical_repository_identity(repository.url),
            "error": repository.error, **repository.stats.model_dump(),
            "contributor_details": [contributor.model_dump() for contributor in repository.contributors],
            "repository_metadata": repository.repository_metadata.model_dump(mode="json"),
            "processing_stats": repository.processing.model_dump(mode="json"),
            "metadata_ready": repository.metadata_ready,
            "files_ready": repository.files_ready,
            "created_at": repository.created_at.isoformat(), "updated_at": repository.updated_at.isoformat(),
        }
        await self._request("POST", "repos?on_conflict=id", json=[payload], headers={**self.headers, "Prefer": "resolution=merge-duplicates"})

    async def list_repositories(self) -> list[Repository]:
        rows = await self._request(
            "GET",
            "repos?select=id,name,full_name,description,owner,branch,language,url,status,error,files,folders,contributors,size_kb,stars,forks,open_issues,open_pull_requests,contributor_details,repository_metadata,processing_stats,metadata_ready,files_ready,created_at,updated_at&order=updated_at.desc",
        )
        return [_repository_from_row(row) for row in rows or []]

    async def get_chunks_by_hash(self, repository_id: UUID, hashes: Iterable[str]) -> dict[str, ChunkRecord]:
        values = ",".join(hashes)
        if not values:
            return {}
        rows = await self._request("GET", f"chunks?repo_id=eq.{repository_id}&content_hash=in.({values})&select=content_hash,content,embedding,chunk_metadata(*)")
        result: dict[str, ChunkRecord] = {}
        for row in rows or []:
            metadata = row.get("chunk_metadata") or {}
            embedding = row["embedding"]
            if isinstance(embedding, str):
                embedding = json.loads(embedding)
            result[row["content_hash"]] = ChunkRecord(row["content_hash"], row["content"], embedding, metadata)
        return result

    async def upsert_chunks(self, repository_id: UUID, records: Iterable[ChunkRecord]) -> None:
        records = list(records)
        if not records:
            return
        chunks = [{"repo_id": str(repository_id), "content_hash": record.content_hash, "content": record.content, "embedding": record.embedding} for record in records]
        rows = await self._request("POST", "chunks?on_conflict=repo_id,content_hash", json=chunks, headers={**self.headers, "Prefer": "resolution=merge-duplicates,return=representation"})
        ids_by_hash = {row["content_hash"]: row["id"] for row in rows or []}
        metadata_rows = []
        for record in records:
            metadata = record.metadata
            metadata_rows.append({"chunk_id": ids_by_hash[record.content_hash], "filepath": metadata.get("filepath", ""), "language": metadata.get("language"), "symbol": metadata.get("symbol"), "symbol_type": metadata.get("symbol_type"), "class_name": metadata.get("class_name"), "parent_symbol": metadata.get("parent_symbol"), "start_line": metadata.get("start_line"), "end_line": metadata.get("end_line"), "imports": metadata.get("imports", [])})
        await self._request("POST", "chunk_metadata?on_conflict=chunk_id", json=metadata_rows, headers={**self.headers, "Prefer": "resolution=merge-duplicates"})

    async def delete_stale_chunks(self, repository_id: UUID, current_hashes: set[str]) -> None:
        if not current_hashes:
            await self._request("DELETE", f"chunks?repo_id=eq.{repository_id}")
            return
        values = ",".join(current_hashes)
        await self._request("DELETE", f"chunks?repo_id=eq.{repository_id}&content_hash=not.in.({values})")

    async def upsert_file(self, repository_id: UUID, path: str, content: str) -> None:
        await self._request(
            "POST",
            "repository_files?on_conflict=repo_id,path",
            json=[{"repo_id": str(repository_id), "path": path, "content": content}],
            headers={**self.headers, "Prefer": "resolution=merge-duplicates"},
        )

    async def get_files(self, repository_id: UUID) -> dict[str, str]:
        rows = await self._request("GET", f"repository_files?repo_id=eq.{repository_id}&select=path,content&order=path")
        return {row["path"]: row["content"] for row in rows or []}

    async def log_event(self, repository_id: UUID | None, stage: str, level: str, message: str, metadata: dict[str, Any] | None = None, latency_ms: float | None = None) -> None:
        await self._request("POST", "logs", json=[{"repo_id": str(repository_id) if repository_id else None, "stage": stage, "level": level, "message": redact_sensitive(message), "metadata": redact_sensitive(metadata or {}), "latency_ms": latency_ms}])

    async def get_semantic_cache(self, repo_id: UUID, query_embedding: list[float], threshold: float) -> dict[str, Any] | None:
        rows = await self._request("POST", "rpc/match_semantic_cache", json={"p_repo_id": str(repo_id), "p_query_embedding": query_embedding, "p_similarity_threshold": threshold})
        return rows[0]["response"] if rows else None

    async def save_semantic_cache(self, repo_id: UUID, query: str, query_embedding: list[float], response: dict[str, Any]) -> None:
        query_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
        payload = [{"repo_id": str(repo_id), "query_hash": query_hash, "query_text": query, "query_embedding": query_embedding, "response": response}]
        await self._request("POST", "semantic_cache?on_conflict=repo_id,query_hash", json=payload, headers={**self.headers, "Prefer": "resolution=merge-duplicates"})

    async def dense_search(self, repo_id: UUID, query_embedding: list[float], limit: int) -> list[dict[str, Any]]:
        return await self._request("POST", "rpc/match_chunks", json={"query_embedding": query_embedding, "match_repo_id": str(repo_id), "match_count": min(limit, 20)})

    async def sparse_search(self, repo_id: UUID, query: str, limit: int) -> list[dict[str, Any]]:
        return await self._request("POST", "rpc/search_chunks", json={"search_query": query, "match_repo_id": str(repo_id), "match_count": min(limit, 20)})

    async def list_evaluation_chunks(self, repo_id: UUID) -> list[dict[str, Any]]:
        rows = await self._request("GET", f"chunks?repo_id=eq.{repo_id}&select=content_hash,content,embedding,chunk_metadata(*)&order=id")
        chunks = []
        for row in rows or []:
            metadata = row.get("chunk_metadata") or {}
            embedding = row.get("embedding")
            if isinstance(embedding, str):
                embedding = json.loads(embedding)
            chunks.append({"content_hash": row["content_hash"], "content": row["content"], "embedding": embedding or [], **metadata})
        return chunks

    async def claim_evaluation(self, repo_id: UUID, eval_version: str) -> bool:
        existing = await self._request("GET", f"eval_results?repo_id=eq.{repo_id}&eval_version=eq.{eval_version}&select=status&limit=1")
        if existing:
            if existing[0].get("status") != "failed":
                return False
            await self._request("PATCH", f"eval_results?repo_id=eq.{repo_id}&eval_version=eq.{eval_version}", json={"status": "running", "error": None, "completed_at": None}, headers={**self.headers, "Prefer": "return=minimal"})
            return True
        rows = await self._request("POST", "eval_results?on_conflict=repo_id,eval_version", json=[{"repo_id": str(repo_id), "eval_version": eval_version, "status": "running"}], headers={**self.headers, "Prefer": "resolution=ignore-duplicates,return=representation"})
        return bool(rows)

    async def save_golden_examples(self, repo_id: UUID, eval_version: str, examples: list[Any]) -> None:
        if not examples:
            return
        rows = []
        for example in examples:
            question_embedding = example.question_embedding
            if question_embedding is not None and len(question_embedding) != 768:
                question_embedding = None
            rows.append({"repo_id": str(repo_id), "eval_version": eval_version, "question_hash": hashlib.sha256(example.question.strip().lower().encode("utf-8")).hexdigest(), "question": example.question, "answer": example.answer, "ground_truth": {"content_hash": example.ground_truth.content_hash, "filepath": example.ground_truth.filepath, "symbol": example.ground_truth.symbol, "symbol_type": example.ground_truth.symbol_type, "start_line": example.ground_truth.start_line, "end_line": example.ground_truth.end_line}, "question_embedding": question_embedding, "validation_score": example.validation_score})
        await self._request("POST", "eval_golden_set?on_conflict=repo_id,eval_version,question_hash", json=rows, headers={**self.headers, "Prefer": "resolution=merge-duplicates"})

    async def finish_evaluation(self, repo_id: UUID, eval_version: str, payload: dict[str, Any]) -> None:
        update = {key: payload[key] for key in ("status", "generated_count", "accepted_count", "rejected_count", "query_count", "successful_count", "failed_count", "recall_at_5", "precision_at_5", "mrr", "latency_stats", "per_query", "error") if key in payload}
        update["completed_at"] = datetime.now(timezone.utc).isoformat()
        await self._request("PATCH", f"eval_results?repo_id=eq.{repo_id}&eval_version=eq.{eval_version}", json=update, headers={**self.headers, "Prefer": "return=minimal"})

    async def save_session(self, session: ChatSession) -> None:
        await self._request("POST", "chat_sessions?on_conflict=id", json=[{
            "id": str(session.id), "repository_id": str(session.repository_id),
            "created_at": session.created_at.isoformat(), "updated_at": session.updated_at.isoformat(),
        }], headers={**self.headers, "Prefer": "resolution=merge-duplicates"})

    async def get_sessions(self, repository_id: UUID) -> list[ChatSession]:
        rows = await self._request("GET", f"chat_sessions?repository_id=eq.{repository_id}&select=id,repository_id,created_at,updated_at&order=updated_at.asc")
        return [_session_from_row(row) for row in rows or []]

    async def get_session(self, session_id: UUID) -> ChatSession | None:
        rows = await self._request("GET", f"chat_sessions?id=eq.{session_id}&select=id,repository_id,created_at,updated_at&limit=1")
        return _session_from_row(rows[0]) if rows else None

    async def save_message(self, session_id: UUID, message: ChatMessage) -> None:
        await self._request("POST", "chat_messages?on_conflict=id", json=[{
            "id": str(message.id), "session_id": str(session_id), "role": message.role,
            "content": message.content, "citations": message.citations, "created_at": message.created_at.isoformat(),
        }], headers={**self.headers, "Prefer": "resolution=merge-duplicates"})

    async def get_messages(self, session_id: UUID) -> list[ChatMessage]:
        rows = await self._request("GET", f"chat_messages?session_id=eq.{session_id}&select=id,role,content,citations,created_at&order=created_at.asc")
        return [ChatMessage(id=UUID(str(row["id"])), role=row["role"], content=row["content"], citations=row.get("citations") or [], created_at=row["created_at"]) for row in rows or []]

    async def delete_sessions(self, repository_id: UUID) -> None:
        await self._request("DELETE", f"chat_sessions?repository_id=eq.{repository_id}")


def _repository_from_row(row: dict[str, Any]) -> Repository:
    return Repository(
        id=UUID(str(row["id"])),
        name=row["name"],
        full_name=row.get("full_name"),
        description=row.get("description"),
        owner=row.get("owner"),
        branch=row.get("branch"),
        language=row.get("language"),
        url=row["url"],
        repository_key=row.get("repository_key") or canonical_repository_identity(row["url"]),
        stats=RepositoryStats(
            files=row.get("files", 0),
            folders=row.get("folders", 0),
            contributors=row.get("contributors", 0),
            size_kb=row.get("size_kb"),
            stars=row.get("stars", 0),
            forks=row.get("forks", 0),
            open_issues=row.get("open_issues", 0),
            open_pull_requests=row.get("open_pull_requests"),
        ),
        contributors=row.get("contributor_details") or [],
        repository_metadata=RepositoryMetadata.model_validate(row.get("repository_metadata") or {}),
        processing=ProcessingStats.model_validate(row.get("processing_stats") or {}),
        metadata_ready=row.get("metadata_ready", False),
        files_ready=row.get("files_ready", False),
        status=row["status"],
        error=row.get("error"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _session_from_row(row: dict[str, Any]) -> ChatSession:
    return ChatSession(
        id=UUID(str(row["id"])),
        repository_id=UUID(str(row["repository_id"])),
        created_at=row["created_at"],
        updated_at=row.get("updated_at") or row["created_at"],
    )
