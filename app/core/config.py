"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import DEFAULT_APP_NAME, DEFAULT_APP_VERSION

LlmProviderName = Literal["gemini_api", "openai", "vertex_ai", "fake"]
LlmProvider = LlmProviderName
EmbeddingProviderName = Literal["gemini_api", "openai", "vertex_ai", "fake"]
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
    qdrant_api_key: SecretStr = SecretStr("")
    qdrant_collection_name: str = "samadhan_policies"
    redis_url: str = ""

    secret_key: SecretStr = SecretStr("")
    session_cookie_name: str = "samadhan_session"

    llm_provider: LlmProviderName = "gemini_api"
    llm_fallback_enabled: bool = False
    llm_fallback_provider: LlmProviderName | None = None
    llm_max_provider_attempts: int = Field(default=2, ge=1, le=3)
    llm_request_timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)
    embedding_provider: EmbeddingProviderName = "gemini_api"
    gemini_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-2.0-flash"
    openai_model: str = "gpt-4o-mini"
    gemini_embedding_model: str = "text-embedding-004"
    openai_embedding_model: str = "text-embedding-3-small"
    vertex_embedding_model: str = "text-embedding-004"
    fake_embedding_dimension: int = Field(default=768, ge=8, le=4096)

    vertex_ai_project_id: str = ""
    vertex_ai_location: str = "us-central1"
    vertex_ai_model: str = "gemini-flash-class-model"

    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr = SecretStr("")
    langsmith_project: str = "samadhan-dev"

    max_messages_per_user_per_day: int = Field(default=20, ge=1, le=1000)
    max_llm_calls_per_day: int = Field(default=100, ge=1, le=10000)
    max_output_tokens: int = Field(default=800, ge=1, le=4096)

    intent_classifier_llm_fallback_enabled: bool = True
    intent_classifier_rule_accept_threshold: float = Field(default=0.75, ge=0.5, le=1.0)
    intent_classifier_min_llm_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    intent_classifier_ambiguity_gap: float = Field(default=0.15, ge=0.0, le=0.5)

    rag_chunk_size_chars: int = Field(default=3500, ge=500, le=20000)
    rag_chunk_overlap_chars: int = Field(default=500, ge=0, le=5000)
    rag_chunk_min_chars: int = Field(default=50, ge=1, le=1000)

    rag_default_top_k: int = Field(default=5, ge=1, le=20)
    rag_max_top_k: int = Field(default=10, ge=1, le=50)
    rag_default_min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    rag_query_max_chars: int = Field(default=2000, ge=32, le=10000)
    qdrant_request_timeout_seconds: float = Field(default=5.0, ge=0.5, le=60.0)

    storage_backend: StorageBackend = "local"
    local_storage_path: str = "storage"
    gcs_bucket_name: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
