import asyncio
from typing import Any

from .retrieval import RetrievalError, RetrievalResult


class CrossEncoderReranker:
    """Lazy cross-encoder boundary; model loading never occurs during module import."""

    def __init__(self, model_name: str, model: Any | None = None) -> None:
        self.model_name = model_name
        self._model = model

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from langchain_community.cross_encoders import HuggingFaceCrossEncoder
            except ImportError as exc:
                raise RetrievalError("langchain-community and sentence-transformers are required for cross-encoder reranking.") from exc
            self._model = HuggingFaceCrossEncoder(model_name=self.model_name)
        return self._model

    async def rerank(self, query: str, candidates: list[RetrievalResult], limit: int) -> list[RetrievalResult]:
        if not candidates:
            return []
        pairs = [(query, candidate.content) for candidate in candidates]
        try:
            scores = await asyncio.to_thread(self._load_model().score, pairs)
            values = [float(score) for score in scores]
        except Exception as exc:
            raise RetrievalError(f"Cross-encoder model failed: {exc}") from exc
        if len(values) != len(candidates):
            raise RetrievalError("Cross-encoder returned the wrong number of scores.")
        ranked = sorted(zip(candidates, values, strict=True), key=lambda item: (-item[1], str(item[0].chunk_id)))
        results = []
        for rank, (candidate, score) in enumerate(ranked[:limit], start=1):
            candidate.reranker_score = score
            candidate.reranker_rank = rank
            results.append(candidate)
        return results
