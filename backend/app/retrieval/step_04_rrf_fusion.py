from typing import Any
from app.schemas.retrieval import RetrievalResult


class RRFFusion:
    """Reciprocal Rank Fusion (RRF) combining dense vector and sparse keyword rankings."""

    def __init__(self, k: int = 60, dense_weight: float = 0.5, sparse_weight: float = 0.5) -> None:
        self.k = k
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

    def fuse(
        self,
        dense_results: list[RetrievalResult],
        sparse_results: list[RetrievalResult],
        top_k: int = 20,
    ) -> list[RetrievalResult]:
        """Combine two ranked lists using weighted Reciprocal Rank Fusion."""
        fused_scores: dict[str, float] = {}
        result_map: dict[str, RetrievalResult] = {}

        # Process dense rankings
        for rank, item in enumerate(dense_results, start=1):
            key = self._chunk_key(item)
            rrf = self.dense_weight * (1.0 / (self.k + rank))
            fused_scores[key] = fused_scores.get(key, 0.0) + rrf
            result_map[key] = item

        # Process sparse rankings
        for rank, item in enumerate(sparse_results, start=1):
            key = self._chunk_key(item)
            rrf = self.sparse_weight * (1.0 / (self.k + rank))
            fused_scores[key] = fused_scores.get(key, 0.0) + rrf
            if key not in result_map:
                result_map[key] = item
            else:
                result_map[key].sparse_score = item.sparse_score

        # Sort combined results by descending RRF score
        sorted_keys = sorted(fused_scores.keys(), key=lambda k: fused_scores[k], reverse=True)
        fused: list[RetrievalResult] = []
        for key in sorted_keys[:top_k]:
            res = result_map[key]
            res.score = fused_scores[key]
            fused.append(res)

        return fused

    @staticmethod
    def _chunk_key(result: RetrievalResult) -> str:
        c = result.chunk
        if c.chunk_id and str(c.chunk_id) != "00000000-0000-0000-0000-000000000000":
            return str(c.chunk_id)
        return f"{c.filepath}:{c.start_line}-{c.end_line}:{hash(c.content)}"
