"""LLM provider protocol, errors, and factory (T-046)."""

from __future__ import annotations

from typing import Protocol

from app.core.config import LlmProviderName, Settings, get_settings
from app.providers.llm_schemas import LlmGenerationResult, LlmRequest


class LlmProviderError(Exception):
    """Raised when LLM configuration or provider resolution fails safely."""

    def __init__(
        self,
        message: str,
        *,
        category: str | None = None,
        retryable: bool = False,
    ) -> None:
        self.message = message
        self.category = category
        self.retryable = retryable
        super().__init__(message)


class LlmProvider(Protocol):
    """Common LLM text-generation provider contract."""

    provider_name: str
    model_name: str

    def is_configured(self) -> bool: ...

    async def generate(self, request: LlmRequest) -> LlmGenerationResult: ...


def get_llm_provider(
    settings: Settings | None = None,
    *,
    provider_name: LlmProviderName | None = None,
) -> LlmProvider:
    """Return the configured LLM provider without performing network I/O."""
    from app.providers.fake_llm import FakeLlmProvider
    from app.providers.gemini_llm import GeminiLlmProvider
    from app.providers.openai_llm import OpenAILlmProvider
    from app.providers.vertex_llm import VertexLlmProvider

    resolved = settings or get_settings()
    selected = provider_name or resolved.llm_provider
    match selected:
        case "fake":
            return FakeLlmProvider(resolved)
        case "gemini_api":
            return GeminiLlmProvider(resolved)
        case "openai":
            return OpenAILlmProvider(resolved)
        case "vertex_ai":
            return VertexLlmProvider(resolved)
        case _:
            raise LlmProviderError(f"unsupported LLM provider: {selected}")
