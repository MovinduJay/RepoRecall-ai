from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RepoRecall API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+asyncpg://reporecall:reporecall@localhost:5432/reporecall"
    )
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "engineering_history"

    github_token: str | None = Field(default=None, repr=False)
    github_api_url: str = "https://api.github.com"
    github_api_version: str = "2026-03-10"
    github_max_items_per_source: int = Field(default=100, ge=1, le=500)
    worker_poll_interval_seconds: float = Field(default=3.0, gt=0)

    openai_api_key: str | None = Field(default=None, repr=False)
    openai_model: str = "gpt-5-nano"
    ollama_base_url: str | None = None
    ollama_model: str = "qwen2.5:3b"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
