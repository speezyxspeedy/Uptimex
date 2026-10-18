import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "UptimeX"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    DATABASE_URL: str = "sqlite:///./uptimex.db"
    
    MAX_CONCURRENT_CHECKS: int = 10
    DEFAULT_CHECK_INTERVAL_SECONDS: int = 60
    DEFAULT_TIMEOUT_SECONDS: int = 10
    DATA_RETENTION_DAYS: int = 30
    
    # CORS: Narrow to local origins by default
    ALLOWED_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
