import hashlib
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from langchain_core.documents import Document

from .embeddings import EmbeddingProviderError

StageCallback = Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class ChunkRecord:
    content_hash: str
    content: str
    embedding: list[float]
    metadata: dict[str, Any]


def content_hash(document: Document) -> str:
    return hashlib.sha256(document.page_content.encode("utf-8")).hexdigest()


class IndexingService:
    def __init__(self, persistence: Any) -> None:
        self.persistence = persistence

    async def index_documents(
        self,
        repository_id: UUID,
        documents: Sequence[Document],
        embedder: Any,
        on_stage: StageCallback | None = None,
    ) -> dict[str, int]:
        unique_documents: dict[str, Document] = {}
        for document in documents:
            unique_documents.setdefault(content_hash(document), document)
        hashes = list(unique_documents)
        existing = await self.persistence.get_chunks_by_hash(repository_id, hashes)
        missing_hashes = [chunk_hash for chunk_hash in hashes if chunk_hash not in existing]

        if on_stage is not None:
            await on_stage("embedding")
        vectors: dict[str, list[float]] = {
            chunk_hash: stored.embedding
            for chunk_hash, stored in existing.items()
            if stored.embedding
        }
        if missing_hashes:
            embedded = await embedder.embed_documents([unique_documents[chunk_hash].page_content for chunk_hash in missing_hashes])
            if len(embedded) != len(missing_hashes):
                raise EmbeddingProviderError("Embedding provider returned the wrong number of vectors.")
            vectors.update(dict(zip(missing_hashes, embedded, strict=True)))

        if on_stage is not None:
            await on_stage("indexing")
        records = [
            ChunkRecord(
                content_hash=chunk_hash,
                content=document.page_content,
                embedding=vectors[chunk_hash],
                metadata=document.metadata,
            )
            for chunk_hash, document in unique_documents.items()
        ]
        await self.persistence.upsert_chunks(repository_id, records)
        await self.persistence.delete_stale_chunks(repository_id, set(hashes))
        return {"total": len(records), "embedded": len(missing_hashes), "reused": len(records) - len(missing_hashes)}
