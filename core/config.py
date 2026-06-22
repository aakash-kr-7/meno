"""
(a) What this file is: Centralized configuration management for the MENO platform.
(b) What it does: Centralized config via Pydantic Settings. Single source of truth. Never read os.environ directly.
(c) How it fits into the MENO system: Provides configuration settings for database connections, caching, embeddings, LLMs, and MCP settings.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    DATABASE_URL: str = Field(default="postgresql+asyncpg://meno:meno@localhost:5432/meno")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    SECRET_KEY: str = Field(default="change_me_in_production")
    API_KEY_HEADER: str = Field(default="X-API-Key")
    EMBEDDING_MODEL: str = Field(default="BAAI/bge-small-en-v1.5")
    EMBEDDING_DIM: int = Field(default=384)
    SESSION_TTL_SECONDS: int = Field(default=86400)
    PROMOTION_THRESHOLD: int = Field(default=20)
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    CORS_ORIGINS: str = Field(default="http://localhost:3000")
    LLM_EXTRACTION_ENABLED: bool = Field(default=False)
    LLM_API_KEY: str = Field(default="")
    LLM_MODEL: str = Field(default="claude-sonnet-4-6")
    MENO_MCP_TRANSPORT: str = Field(default="stdio")
    MENO_MCP_HOST: str = Field(default="0.0.0.0")
    MENO_MCP_PORT: int = Field(default=8765)

    @property
    def app_env(self) -> str:
        """Alias for APP_ENV to match the health check requirements."""
        return self.APP_ENV

    @property
    def secret_key(self) -> str:
        """Alias for SECRET_KEY to support lowercase settings reference."""
        return self.SECRET_KEY

    @property
    def api_key_header(self) -> str:
        """Alias for API_KEY_HEADER to support lowercase settings reference."""
        return self.API_KEY_HEADER


settings = Settings()
