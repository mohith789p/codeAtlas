from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ChunkRecord(BaseModel):
    chunk_id: UUID = Field(default_factory=uuid4)
    content_hash: str
    content: str
    filepath: str
    language: str | None = None
    symbol: str | None = None
    symbol_type: str | None = None
    class_name: str | None = None
    parent_symbol: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    imports: list[str] = Field(default_factory=list)
    embedding: list[float] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    chunk: ChunkRecord
    score: float
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rerank_score: float = 0.0


class CacheEntry(BaseModel):
    query_text: str
    similarity: float
    response: dict[str, Any]
    hit: bool = True
