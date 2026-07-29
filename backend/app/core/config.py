import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Find and load .env file from current directory or parent directories
env_path = find_dotenv(usecwd=True)
if env_path:
    load_dotenv(env_path, override=True)
else:
    # Fallback search root directory
    root_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "CodeAtlas"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./codeatlas.db")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecretjwtkey12345")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def get_gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", self.GEMINI_API_KEY)

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
