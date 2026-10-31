import logging
from typing import Any

from app.schemas.retrieval import RetrievalResult
from app.shared.config import Settings, get_settings

logger = logging.getLogger(__name__)

_CROSS_ENCODER_MODEL: Any = None


def get_cross_encoder(model_name: str) -> Any | None:
    """Lazily load and cache SentenceTransformer CrossEncoder."""
    global _CROSS_ENCODER_MODEL
    if _CROSS_ENCODER_MODEL is None:
        try:
            from sentence_transformers import CrossEncoder
            _CROSS_ENCODER_MODEL = CrossEncoder(model_name)
            logger.info("Loaded CrossEncoder model: %s", model_name)
        except Exception as exc:
            logger.warning("Failed to load CrossEncoder (%s); falling back to RRF: %s", model_name, exc)
            _CROSS_ENCODER_MODEL = False
    return _CROSS_ENCODER_MODEL if _CROSS_ENCODER_MODEL is not False else None


class CrossEncoderReranker:
    """Deep cross-attention scoring using ms-marco-MiniLM-L-6-v2."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def rerank(
        self, query: str, candidates: list[RetrievalResult], top_k: int = 4
    ) -> list[RetrievalResult]:
        """Score (query, chunk_content) pairs and return top_k candidates."""
        if not candidates:
            return []
        if len(candidates) <= 1:
            return candidates[:top_k]

        model = get_cross_encoder(self.settings.reranker_model)
        if model is None:
            return candidates[:top_k]

        pairs = [[query, item.chunk.content] for item in candidates]
        try:
            scores = model.predict(pairs)
            for item, s in zip(candidates, scores):
                item.rerank_score = float(s)
                item.score = float(s)

            candidates.sort(key=lambda x: x.rerank_score, reverse=True)
            return candidates[:top_k]
        except Exception as exc:
            logger.warning("Reranking prediction failed; keeping RRF ordering: %s", exc)
            return candidates[:top_k]
