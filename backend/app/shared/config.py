from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # GitHub
    github_api_url: str = "https://api.github.com"
    github_token: str | None = None
    max_repository_size_kb: int = 512_000
    download_read_timeout_seconds: float = 30.0
    download_chunk_size_bytes: int = 1_048_576
    max_file_size_bytes: int = 1_048_576

    # Supabase / PostgreSQL
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    # Embeddings (Gemini 768-d)
    gemini_api_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_api_key: str | None = None
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    embedding_batch_size: int = 16
    embedding_timeout_seconds: float = 30.0
    gemini_embedding_rpm_limit: int = 60
    gemini_embedding_max_retries: int = 5

    # 4-Tier Generation Provider Chain
    gemini_generation_model: str = "gemini-2.5-flash"
    groq_api_url: str = "https://api.groq.com/openai/v1"
    groq_api_key: str | None = None
    groq_generation_model: str = "llama-3.3-70b-versatile"
    cerebras_api_url: str = "https://api.cerebras.ai/v1"
    cerebras_api_key: str | None = None
    cerebras_generation_model: str = "llama-3.3-70b"
    openrouter_api_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str | None = None
    openrouter_generation_model: str = "openai/gpt-4o-mini"

    # Retrieval & Reranking
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    retrieval_dense_weight: float = 0.5
    retrieval_sparse_weight: float = 0.5
    retrieval_top_k: int = 4
    semantic_cache_threshold: float = 0.92

    # LangSmith Observability
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "codeatlas"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_environment: str = "development"

    # CORS
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="CODE_ATLAS_", extra="ignore"
    )

    @property
    def is_langsmith_enabled(self) -> bool:
        return bool(self.langsmith_tracing or (self.langsmith_api_key and self.langsmith_api_key.strip()))

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
