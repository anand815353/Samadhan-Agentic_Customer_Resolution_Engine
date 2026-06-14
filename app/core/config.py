"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import DEFAULT_APP_NAME, DEFAULT_APP_VERSION

LlmProvider = Literal["gemini_api", "openai", "vertex_ai"]
StorageBackend = Literal["local", "gcs"]


class Settings(BaseSettings):
    """Application and infrastructure settings with safe local-first defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = DEFAULT_APP_NAME
    app_env: str = "local"
    app_debug: bool = True
    app_base_url: str = "http://localhost:8000"
    app_version: str = DEFAULT_APP_VERSION
    log_level: str = "INFO"
    log_json: bool = False

    mongodb_uri: str = ""
    mongodb_db_name: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    redis_url: str = ""

    secret_key: SecretStr = SecretStr("")
    session_cookie_name: str = "samadhan_session"

    llm_provider: LlmProvider = "gemini_api"
    embedding_provider: LlmProvider = "gemini_api"
    gemini_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")

    vertex_ai_project_id: str = ""
    vertex_ai_location: str = "us-central1"
    vertex_ai_model: str = "gemini-flash-class-model"

    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr = SecretStr("")
    langsmith_project: str = "samadhan-dev"

    max_messages_per_user_per_day: int = Field(default=20, ge=1, le=1000)
    max_llm_calls_per_day: int = Field(default=100, ge=1, le=10000)
    max_output_tokens: int = Field(default=800, ge=1, le=4096)

    storage_backend: StorageBackend = "local"
    local_storage_path: str = "storage"
    gcs_bucket_name: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
