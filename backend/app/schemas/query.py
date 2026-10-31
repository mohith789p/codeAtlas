from uuid import UUID
from pydantic import BaseModel, Field


class QueryOptions(BaseModel):
    top_k: int = Field(default=4, ge=1, le=20)
    use_cache: bool = True
    similarity_threshold: float = Field(default=0.92, ge=0.0, le=1.0)
    dense_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    sparse_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class QueryRequest(BaseModel):
    repository_id: UUID
    query: str = Field(min_length=1, max_length=2000)
    options: QueryOptions = Field(default_factory=QueryOptions)
