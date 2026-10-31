import logging
from uuid import UUID

from app.database.repositories import DatabaseRepository
from app.schemas.retrieval import ChunkRecord

logger = logging.getLogger(__name__)


class ChunkDeduplicator:
    """Filters duplicate chunks within a batch and against existing DB embeddings."""

    def __init__(self, db_repo: DatabaseRepository | None = None) -> None:
        self.db_repo = db_repo or DatabaseRepository()

    async def deduplicate(
        self, repo_id: UUID, chunks: list[ChunkRecord]
    ) -> tuple[list[ChunkRecord], list[ChunkRecord]]:
        """Partition chunks into (new_chunks, existing_chunks) using SHA-256 hashes."""
        if not chunks:
            return [], []

        # Step 1: In-memory unique by content_hash
        unique_batch_map: dict[str, ChunkRecord] = {}
        for chunk in chunks:
            if chunk.content_hash not in unique_batch_map:
                unique_batch_map[chunk.content_hash] = chunk

        hashes = list(unique_batch_map.keys())

        # Step 2: Query database for existing hashes to avoid redundant embeddings
        existing_map: dict[str, dict] = {}
        try:
            # Query in batches of 100 to avoid URI length overflow
            batch_size = 100
            for i in range(0, len(hashes), batch_size):
                sub_hashes = hashes[i : i + batch_size]
                rows = await self.db_repo.get_chunks_by_hashes(repo_id, sub_hashes)
                for r in rows:
                    existing_map[r["content_hash"]] = r
        except Exception as exc:
            logger.warning("Failed to query existing chunks for deduplication; treating all as new: %s", exc)

        new_chunks: list[ChunkRecord] = []
        existing_chunks: list[ChunkRecord] = []

        for chash, chunk in unique_batch_map.items():
            if chash in existing_map:
                existing_row = existing_map[chash]
                raw_emb = existing_row.get("embedding") or []
                chunk.embedding = raw_emb if isinstance(raw_emb, list) else []
                existing_chunks.append(chunk)
            else:
                new_chunks.append(chunk)

        logger.info(
            "Deduplication completed for repo %s: %d total, %d new, %d cached",
            repo_id,
            len(chunks),
            len(new_chunks),
            len(existing_chunks),
        )
        return new_chunks, existing_chunks
