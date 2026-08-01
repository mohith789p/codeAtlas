import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always resolve the root directory .env file relative to this file's location
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ROOT_ENV_PATH = ROOT_DIR / ".env"

if ROOT_ENV_PATH.exists():
    load_dotenv(ROOT_ENV_PATH, override=True)
else:
    # Fallback to current working directory .env if root .env is absent
    load_dotenv(Path.cwd() / ".env", override=True)


class Settings(BaseSettings):
    PROJECT_NAME: str = "CodeAtlas"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./codeatlas.db")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Gemini Embedding & Rate Limiting Configuration
    GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "3072"))
    GEMINI_MAX_BATCH_SIZE: int = min(int(os.getenv("GEMINI_MAX_BATCH_SIZE", "100")), 250)
    GEMINI_RPM_LIMIT: int = int(os.getenv("GEMINI_RPM_LIMIT", "100"))
    GEMINI_TPM_LIMIT: int = int(os.getenv("GEMINI_TPM_LIMIT", "30000"))
    GEMINI_RPD_LIMIT: int = int(os.getenv("GEMINI_RPD_LIMIT", "1000"))
    
    JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecretjwtkey12345")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    
    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV_PATH) if ROOT_ENV_PATH.exists() else ".env",
        extra="ignore"
    )

    def get_gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", self.GEMINI_API_KEY)


settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
