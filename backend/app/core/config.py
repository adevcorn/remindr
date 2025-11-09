"""Application configuration management."""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/remindr"

    # Google Cloud
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    GOOGLE_CLOUD_PROJECT: str = ""

    # Google OAuth 2.0
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"

    # App Configuration
    SECRET_KEY: str = "change-this-in-production"
    AI_CONFIDENCE_THRESHOLD: float = 0.85
    SYNC_RETRY_MAX_ATTEMPTS: int = 5
    SYNC_RETRY_BACKOFF_BASE: int = 2

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    PROJECT_NAME: str = "Remindr"
    VERSION: str = "0.1.0"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
