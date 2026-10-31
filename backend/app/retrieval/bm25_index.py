import re
from typing import Any
from uuid import UUID

from app.schemas.retrieval import ChunkRecord

_TOKEN_PATTERN = re.compile(r"\w+")


def tokenize(text: str) -> list[str]:
    """Tokenize source code or query text into lowercase words."""
    return _TOKEN_PATTERN.findall(text.lower())


def expand_tokens(tokens: list[str]) -> list[str]:
    """Expand compound code tokens (e.g. snake_case or hyphenated) into sub-tokens."""
    expanded: list[str] = list(tokens)
    for t in tokens:
        if "_" in t:
            expanded.extend([p for p in t.split("_") if p])
        elif "-" in t:
            expanded.extend([p for p in t.split("-") if p])
    return expanded


class BM25Registry:
    """In-memory repository-scoped BM25Okapi index registry."""

    def __init__(self) -> None:
        self._indices: dict[UUID, tuple[Any, list[ChunkRecord]]] = {}
        self._corpus_tokens: dict[UUID, list[list[str]]] = {}

    def has_index(self, repo_id: UUID) -> bool:
        return repo_id in self._indices

    def get_chunks(self, repo_id: UUID) -> list[ChunkRecord]:
        entry = self._indices.get(repo_id)
        if entry:
            return entry[1]
        return []

    def register(self, repo_id: UUID, chunks: list[ChunkRecord]) -> None:
        """Tokenize chunks and build in-memory BM25Okapi index."""
        if not chunks:
            return
        corpus_tokens = [expand_tokens(tokenize(c.content)) for c in chunks]
        self._corpus_tokens[repo_id] = corpus_tokens
        try:
            from rank_bm25 import BM25Okapi
            bm25 = BM25Okapi(corpus_tokens)
            self._indices[repo_id] = (bm25, chunks)
        except ImportError:
            # Fallback placeholder if rank_bm25 package is not available
            self._indices[repo_id] = (corpus_tokens, chunks)

    def query(self, repo_id: UUID, query_text: str, top_k: int = 20) -> list[tuple[ChunkRecord, float]]:
        """Query the in-memory BM25 index and return (chunk, score) tuples."""
        entry = self._indices.get(repo_id)
        if not entry:
            return []
        bm25, chunks = entry
        q_tokens = tokenize(query_text)
        if not q_tokens:
            return []

        if hasattr(bm25, "get_scores"):
            scores = list(bm25.get_scores(q_tokens))
        else:
            # Simple token overlap scoring fallback
            q_set = set(q_tokens)
            scores = [sum(1.0 for t in doc if t in q_set) for doc in bm25]

        # If BM25 scores are all 0 (common in small corpora where BM25Okapi IDF log(1) == 0):
        if max(scores, default=0.0) <= 0.0:
            corpus_tokens = self._corpus_tokens.get(repo_id, [])
            scores = []
            for doc in corpus_tokens:
                match_score = 0.0
                for q in q_tokens:
                    if q in doc:
                        match_score += 1.0
                    elif len(q) >= 4:
                        prefix = q[:4]
                        if any(t.startswith(prefix) or prefix in t for t in doc):
                            match_score += 0.5
                scores.append(match_score)

        scored = list(zip(chunks, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(chunk, float(score)) for chunk, score in scored[:top_k] if score > 0]

    def clear(self, repo_id: UUID | None = None) -> None:
        if repo_id:
            self._indices.pop(repo_id, None)
            self._corpus_tokens.pop(repo_id, None)
        else:
            self._indices.clear()
            self._corpus_tokens.clear()


_registry: BM25Registry | None = None


def get_bm25_registry() -> BM25Registry:
    global _registry
    if _registry is None:
        _registry = BM25Registry()
    return _registry
