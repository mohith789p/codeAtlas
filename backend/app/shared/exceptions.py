"""Domain exceptions for Code Atlas."""


class CodeAtlasError(Exception):
    """Base exception for all domain errors within Code Atlas."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(CodeAtlasError):
    """Raised when required configuration or environment variables are missing."""


class PersistenceError(CodeAtlasError):
    """Raised when a durable storage or database operation fails."""


class RateLimitExceededError(CodeAtlasError):
    """Raised when an external API rate limit is exceeded."""


class ProviderError(CodeAtlasError):
    """Raised when an LLM or embedding provider returns an error."""


class IngestionError(CodeAtlasError):
    """Raised when repository cloning, parsing, or chunking fails."""


class RetrievalError(CodeAtlasError):
    """Raised when hybrid search, reranking, or cache matching fails."""


class CitationValidationError(CodeAtlasError):
    """Raised when generated citations fail grounding or syntax validation."""
