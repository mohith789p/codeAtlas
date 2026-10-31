from app.schemas.response import GenerationResponse, ValidatedCitation


class ResponseFormatter:
    """Formats answer text, validated citations, and telemetry into a unified response schema."""

    def format(
        self,
        answer: str,
        citations: list[ValidatedCitation],
        provider: str,
        model: str,
        cache_hit: bool = False,
        latency_ms: float = 0.0,
        chunks_count: int = 0,
    ) -> GenerationResponse:
        """Construct structured GenerationResponse model."""
        return GenerationResponse(
            answer=answer.strip(),
            citations=citations,
            provider=provider,
            model=model,
            cache_hit=cache_hit,
            latency_ms=round(latency_ms, 2),
            retrieved_chunks_count=chunks_count,
        )
