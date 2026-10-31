import logging
from uuid import UUID

from app.database.repositories import DatabaseRepository
from app.embeddings.embedding_service import EmbeddingService
from app.schemas.retrieval import ChunkRecord

logger = logging.getLogger(__name__)


class ChunkIndexer:
    """Embeds new chunks, upserts records to the database, and hydrates hot BM25 index."""

    def __init__(
        self,
        embedder: EmbeddingService | None = None,
        db_repo: DatabaseRepository | None = None,
    ) -> None:
        self.embedder = embedder or EmbeddingService()
        self.db_repo = db_repo or DatabaseRepository()

    async def index_chunks(
        self, repo_id: UUID, new_chunks: list[ChunkRecord], existing_chunks: list[ChunkRecord]
    ) -> int:
        """Embed new chunks, upsert to DB, and warm BM25 sparse index with all chunks."""
        if new_chunks:
            logger.info("Generating embeddings for %d new chunks in repo %s", len(new_chunks), repo_id)
            texts = [c.content for c in new_chunks]
            embeddings = await self.embedder.embed_documents(texts)
            for chunk, emb in zip(new_chunks, embeddings):
                chunk.embedding = emb

            # Prepare payloads for database upsert
            chunk_rows = [
                {
                    "id": str(c.chunk_id),
                    "repo_id": str(repo_id),
                    "content_hash": c.content_hash,
                    "content": c.content,
                    "embedding": c.embedding,
                }
                for c in new_chunks
            ]
            meta_rows = [
                {
                    "chunk_id": str(c.chunk_id),
                    "filepath": c.filepath,
                    "language": c.language,
                    "symbol": c.symbol,
                    "symbol_type": c.symbol_type,
                    "class_name": c.class_name,
                    "parent_symbol": c.parent_symbol,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "imports": c.imports,
                }
                for c in new_chunks
            ]
            await self.db_repo.upsert_chunks(chunk_rows, meta_rows)
            logger.info("Upserted %d new chunks to database for repo %s", len(new_chunks), repo_id)

        # Warm the in-memory BM25 index with all chunks for instantaneous retrieval
        all_chunks = existing_chunks + new_chunks
        try:
            from app.retrieval.bm25_index import get_bm25_registry
            get_bm25_registry().register(repo_id, all_chunks)
            logger.info("Hydrated in-memory BM25 index for repo %s with %d chunks", repo_id, len(all_chunks))
        except Exception as exc:
            logger.warning("BM25 hot index build deferred or failed for repo %s: %s", repo_id, exc)

        return len(new_chunks)
