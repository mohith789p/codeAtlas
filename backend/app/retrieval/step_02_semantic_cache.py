import logging
from typing import Any
from uuid import UUID

from app.database.repositories import DatabaseRepository
from app.schemas.retrieval import CacheEntry
from app.shared.config import Settings, get_settings

logger = logging.getLogger(__name__)


class SemanticCache:
    """Repository-scoped semantic cache with cosine similarity matching."""

    def __init__(
        self,
        db_repo: DatabaseRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db_repo = db_repo or DatabaseRepository()
        self.settings = settings or get_settings()

    async def lookup(
        self, repo_id: UUID, query: str, query_embedding: list[float], threshold: float | None = None
    ) -> CacheEntry | None:
        """Query semantic cache for vector match >= threshold."""
        thresh = threshold if threshold is not None else self.settings.semantic_cache_threshold
        try:
            cached_response = await self.db_repo.get_semantic_cache(repo_id, query_embedding, thresh)
            if cached_response:
                logger.info("Semantic cache HIT for repo %s (threshold=%.2f)", repo_id, thresh)
                return CacheEntry(query_text=query, similarity=1.0, response=cached_response, hit=True)
        except Exception as exc:
            logger.warning("Semantic cache lookup failed; proceeding with retrieval: %s", exc)
        return None

    async def save(
        self, repo_id: UUID, query: str, query_embedding: list[float], response: dict[str, Any]
    ) -> None:
        """Persist generated answer to semantic cache for future hits."""
        try:
            await self.db_repo.save_semantic_cache(repo_id, query, query_embedding, response)
            logger.info("Saved query to semantic cache for repo %s", repo_id)
        except Exception as exc:
            logger.warning("Failed to save response to semantic cache: %s", exc)
