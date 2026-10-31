import logging
import re
from typing import Any

from app.embeddings.embedding_service import EmbeddingService
from app.shared.exceptions import RetrievalError

logger = logging.getLogger(__name__)
_CLEAN_WS = re.compile(r"\s+")


class QueryPreprocessor:
    """Sanitizes user input and computes dense query vector embeddings."""

    def __init__(self, embedder: EmbeddingService | None = None) -> None:
        self.embedder = embedder or EmbeddingService()

    def sanitize(self, raw_query: str) -> str:
        """Strip invisible chars, normalize whitespace, and constrain length."""
        if not raw_query or not raw_query.strip():
            raise RetrievalError("Query cannot be empty.")
        clean = raw_query.replace("\x00", "").strip()
        clean = _CLEAN_WS.sub(" ", clean)
        if len(clean) > 2000:
            clean = clean[:2000]
        return clean

    async def preprocess(self, raw_query: str) -> tuple[str, list[float]]:
        """Clean query and compute its 768-d dense embedding vector."""
        sanitized = self.sanitize(raw_query)
        try:
            vectors = await self.embedder.embed_documents([sanitized])
            if not vectors or not vectors[0]:
                raise RetrievalError("Embedding service returned empty query vector.")
            return sanitized, vectors[0]
        except Exception as exc:
            logger.error("Failed to embed user query: %s", exc)
            raise RetrievalError(f"Query vector generation failed: {exc}") from exc
