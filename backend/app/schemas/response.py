from pydantic import BaseModel, Field


class ValidatedCitation(BaseModel):
    filepath: str
    start_line: int
    end_line: int
    symbol: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    snippet: str | None = None


class GenerationResponse(BaseModel):
    answer: str
    citations: list[ValidatedCitation] = Field(default_factory=list)
    provider: str
    model: str
    cache_hit: bool = False
    latency_ms: float = 0.0
    retrieved_chunks_count: int = 0
