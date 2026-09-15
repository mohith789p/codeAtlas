from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    github_api_url: str = "https://api.github.com"
    max_repository_size_kb: int = 512_000
    download_connect_timeout_seconds: float = 10.0
    download_read_timeout_seconds: float = 30.0
    download_chunk_size_bytes: int = 1_048_576
    max_file_size_bytes: int = 1_048_576
    cors_origins: str = "http://localhost:5173"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    gemini_api_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_api_key: str | None = None
    gemini_embedding_model: str = "gemini-embedding-001"
    evaluation_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    evaluation_embedding_similarity_threshold: float = 0.35
    gemini_generation_model: str = "gemini-2.5-flash"
    gemini_summary_model: str = "gemini-2.5-flash-lite"
    embedding_dimensions: int = 768
    embedding_batch_size: int = 16
    gemini_embedding_rpm_limit: int = 60
    gemini_embedding_max_retries: int = 5
    gemini_embedding_retry_base_seconds: float = 1.0
    gemini_embedding_retry_max_seconds: float = 60.0
    embedding_timeout_seconds: float = 30.0
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    groq_api_url: str = "https://api.groq.com/openai/v1"
    groq_api_key: str | None = None
    groq_generation_model: str = "llama-3.3-70b-versatile"
    cerebras_api_url: str = "https://api.cerebras.ai/v1"
    cerebras_api_key: str | None = None
    cerebras_generation_model: str = "llama-3.3-70b"
    openrouter_api_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str | None = None
    openrouter_generation_model: str = "openai/gpt-4o-mini"
    memory_context_budget: int = 2_000
    evaluation_target_count: int = 100

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CODE_ATLAS_", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
