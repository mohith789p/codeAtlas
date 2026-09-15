import asyncio
import math
import re
from collections import defaultdict
from uuid import UUID

from langchain_core.documents import Document

from .config import get_settings
from .logging_utils import redact_sensitive
from .models import ChatMessage, ChatSession, IngestionStatus, Repository, canonical_repository_identity, utc_now
from .persistence import PersistenceError, SupabasePersistence
from .services.indexing import ChunkRecord


class InMemoryStore:
    """Replaceable persistence boundary for the first local vertical slice."""

    def __init__(self, persistence: object | None = None) -> None:
        self.repositories: dict[UUID, Repository] = {}
        self.repository_files: dict[UUID, dict[str, str]] = defaultdict(dict)
        self.repository_documents: dict[UUID, list[Document]] = defaultdict(list)
        self.chunks: dict[UUID, dict[str, ChunkRecord]] = defaultdict(dict)
        self.logs: list[dict[str, object]] = []
        self.semantic_cache: dict[UUID, list[dict[str, object]]] = defaultdict(list)
        self.evaluation_runs: set[tuple[UUID, str]] = set()
        self.evaluation_golden: dict[tuple[UUID, str], list[object]] = defaultdict(list)
        self.evaluation_results: dict[tuple[UUID, str], dict[str, object]] = {}
        self.persistence = persistence
        self.sessions: dict[UUID, ChatSession] = {}
        self.messages: dict[UUID, list[ChatMessage]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def save_repository(self, repository: Repository) -> Repository:
        async with self._lock:
            self.repositories[repository.id] = repository
        if self.persistence is not None:
            await self.persistence.upsert_repository(repository)
        return repository

    async def get_or_create_repository(self, repository: Repository) -> tuple[Repository, bool]:
        """Return an existing repository by canonical identity or register a new one.

        The lock closes the check/register race inside this process. The durable
        repository_key uniqueness constraint handles concurrent processes.
        """
        identity = repository.repository_key or canonical_repository_identity(repository.url)
        async with self._lock:
            existing = next(
                (
                    item for item in self.repositories.values()
                    if (item.repository_key or canonical_repository_identity(item.url)) == identity
                ),
                None,
            )
            if existing is None and self.persistence is not None:
                try:
                    persisted = await self.persistence.list_repositories()
                except PersistenceError:
                    persisted = None
                if persisted is not None:
                    self.repositories.update({item.id: item for item in persisted})
                    existing = next(
                        (
                            item for item in persisted
                            if (item.repository_key or canonical_repository_identity(item.url)) == identity
                        ),
                        None,
                    )

            if existing is not None:
                if existing.status is IngestionStatus.FAILED:
                    existing.status = IngestionStatus.QUEUED
                    existing.error = None
                    existing.updated_at = utc_now()
                    if self.persistence is not None:
                        await self.persistence.upsert_repository(existing)
                    return existing, True
                return existing, False

            repository.repository_key = identity
            self.repositories[repository.id] = repository
            try:
                if self.persistence is not None:
                    await self.persistence.upsert_repository(repository)
            except PersistenceError:
                self.repositories.pop(repository.id, None)
                if self.persistence is None:
                    raise
                persisted = await self.persistence.list_repositories()
                self.repositories.update({item.id: item for item in persisted})
                existing = next(
                    (
                        item for item in persisted
                        if (item.repository_key or canonical_repository_identity(item.url)) == identity
                    ),
                    None,
                )
                if existing is None:
                    raise
                return existing, False
            return repository, True

    async def get_repository(self, repository_id: UUID) -> Repository | None:
        return self.repositories.get(repository_id)

    async def list_repositories(self) -> list[Repository]:
        return list(self.repositories.values())

    async def hydrate_repositories(self) -> list[Repository]:
        if self.persistence is None:
            return []
        repositories = await self.persistence.list_repositories()
        async with self._lock:
            self.repositories.update({repository.id: repository for repository in repositories})
        return repositories

    async def save_file(self, repository_id: UUID, path: str, content: str) -> None:
        self.repository_files[repository_id][path] = content
        if self.persistence is not None:
            await self.persistence.upsert_file(repository_id, path, content)

    async def get_files(self, repository_id: UUID) -> dict[str, str]:
        if self.persistence is not None:
            return await self.persistence.get_files(repository_id)
        return self.repository_files.get(repository_id, {})

    async def save_documents(self, repository_id: UUID, documents: list[Document]) -> None:
        self.repository_documents[repository_id] = documents

    async def get_chunks_by_hash(self, repository_id: UUID, hashes: list[str]) -> dict[str, ChunkRecord]:
        if self.persistence is not None:
            return await self.persistence.get_chunks_by_hash(repository_id, hashes)
        return {chunk_hash: self.chunks[repository_id][chunk_hash] for chunk_hash in hashes if chunk_hash in self.chunks[repository_id]}

    async def upsert_chunks(self, repository_id: UUID, records: list[ChunkRecord]) -> None:
        if self.persistence is not None:
            await self.persistence.upsert_chunks(repository_id, records)
        self.chunks[repository_id].update({record.content_hash: record for record in records})

    async def delete_stale_chunks(self, repository_id: UUID, current_hashes: set[str]) -> None:
        if self.persistence is not None:
            await self.persistence.delete_stale_chunks(repository_id, current_hashes)
        self.chunks[repository_id] = {key: value for key, value in self.chunks[repository_id].items() if key in current_hashes}

    async def log_event(self, repository_id: UUID | None, stage: str, level: str, message: str, metadata: dict[str, object] | None = None, latency_ms: float | None = None) -> None:
        safe_message = redact_sensitive(message)
        safe_metadata = redact_sensitive(metadata or {})
        event = {"repository_id": repository_id, "stage": stage, "level": level, "message": safe_message, "metadata": safe_metadata, "latency_ms": latency_ms}
        self.logs.append(event)
        if self.persistence is not None:
            await self.persistence.log_event(repository_id, stage, level, safe_message, safe_metadata, latency_ms)

    async def get_semantic_cache(self, repo_id: UUID, query_embedding: list[float], threshold: float) -> dict[str, object] | None:
        if self.persistence is not None:
            return await self.persistence.get_semantic_cache(repo_id, query_embedding, threshold)
        best: tuple[float, dict[str, object]] | None = None
        for item in self.semantic_cache[repo_id]:
            similarity = _cosine_similarity(query_embedding, item["query_embedding"])
            if similarity >= threshold and (best is None or similarity > best[0]):
                best = (similarity, item["response"])
        return best[1] if best else None

    async def save_semantic_cache(self, repo_id: UUID, query: str, query_embedding: list[float], response: dict[str, object]) -> None:
        if self.persistence is not None:
            await self.persistence.save_semantic_cache(repo_id, query, query_embedding, response)
        self.semantic_cache[repo_id].append({"query": query, "query_embedding": query_embedding, "response": response})

    async def dense_search(self, repo_id: UUID, query_embedding: list[float], limit: int) -> list[dict[str, object]]:
        if self.persistence is not None:
            return await self.persistence.dense_search(repo_id, query_embedding, limit)
        rows = []
        for record in self.chunks[repo_id].values():
            similarity = _cosine_similarity(query_embedding, record.embedding)
            rows.append(_record_row(record, similarity=similarity))
        return sorted(rows, key=lambda row: (-row["similarity"], str(row["id"])))[:min(limit, 20)]

    async def sparse_search(self, repo_id: UUID, query: str, limit: int) -> list[dict[str, object]]:
        if self.persistence is not None:
            return await self.persistence.sparse_search(repo_id, query, limit)
        terms = set(re.findall(r"[A-Za-z0-9_]+", query.lower()))
        rows = []
        for record in self.chunks[repo_id].values():
            metadata = record.metadata
            symbol = str(metadata.get("symbol") or "")
            haystack = f"{record.content} {symbol}".lower()
            score = float(sum(haystack.count(term) for term in terms))
            if symbol.lower() == query.lower():
                score += 100.0
            if score:
                rows.append(_record_row(record, rank_score=score))
        return sorted(rows, key=lambda row: (-row["rank_score"], str(row["id"])))[:min(limit, 20)]

    async def list_evaluation_chunks(self, repo_id: UUID) -> list[dict[str, object]]:
        if self.persistence is not None:
            return await self.persistence.list_evaluation_chunks(repo_id)
        return [{"content_hash": record.content_hash, "content": record.content, "embedding": record.embedding, **record.metadata} for record in self.chunks[repo_id].values()]

    async def claim_evaluation(self, repo_id: UUID, eval_version: str) -> bool:
        if self.persistence is not None:
            return await self.persistence.claim_evaluation(repo_id, eval_version)
        key = (repo_id, eval_version)
        if key in self.evaluation_runs and self.evaluation_results.get(key, {}).get("status") != "failed":
            return False
        self.evaluation_runs.add(key)
        self.evaluation_results[key] = {"status": "running"}
        return True

    async def save_golden_examples(self, repo_id: UUID, eval_version: str, examples: list[object]) -> None:
        if self.persistence is not None:
            await self.persistence.save_golden_examples(repo_id, eval_version, examples)
        self.evaluation_golden[(repo_id, eval_version)] = examples

    async def finish_evaluation(self, repo_id: UUID, eval_version: str, payload: dict[str, object]) -> None:
        if self.persistence is not None:
            await self.persistence.finish_evaluation(repo_id, eval_version, payload)
        self.evaluation_results[(repo_id, eval_version)] = payload

    async def save_session(self, session: ChatSession) -> ChatSession:
        self.sessions[session.id] = session
        if self.persistence is not None:
            await self.persistence.save_session(session)
        return session

    async def get_session(self, session_id: UUID) -> ChatSession | None:
        session = self.sessions.get(session_id)
        if session is None and self.persistence is not None:
            session = await self.persistence.get_session(session_id)
            if session is not None:
                self.sessions[session.id] = session
        return session

    async def get_sessions(self, repository_id: UUID) -> list[ChatSession]:
        if self.persistence is not None:
            sessions = await self.persistence.get_sessions(repository_id)
            self.sessions.update({session.id: session for session in sessions})
            return sessions
        return [session for session in self.sessions.values() if session.repository_id == repository_id]

    async def add_message(self, message: ChatMessage, session_id: UUID) -> ChatMessage:
        self.messages[session_id].append(message)
        if self.persistence is not None:
            await self.persistence.save_message(session_id, message)
        return message

    async def get_messages(self, session_id: UUID) -> list[ChatMessage]:
        if self.persistence is not None:
            messages = await self.persistence.get_messages(session_id)
            self.messages[session_id] = messages
            return messages
        return self.messages.get(session_id, [])

    async def delete_sessions(self, repository_id: UUID) -> None:
        session_ids = [session.id for session in self.sessions.values() if session.repository_id == repository_id]
        for session_id in session_ids:
            self.sessions.pop(session_id, None)
            self.messages.pop(session_id, None)
        if self.persistence is not None:
            await self.persistence.delete_sessions(repository_id)


def _configured_persistence() -> object | None:
    settings = get_settings()
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabasePersistence(settings)
    return None


store = InMemoryStore(persistence=_configured_persistence())


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


def _record_row(record: ChunkRecord, **scores: float) -> dict[str, object]:
    metadata = record.metadata
    return {"id": record.content_hash, "repo_id": metadata.get("repo_id"), "content": record.content, **scores, **metadata}
