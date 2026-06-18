"""Schemas for LLM text-generation provider requests and responses (T-046)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

LlmMessageRole = Literal["system", "user", "assistant"]
LlmErrorCategory = Literal[
    "provider_not_configured",
    "provider_unavailable",
    "authentication_error",
    "invalid_request",
    "timeout",
    "rate_limited",
    "safety_blocked",
    "malformed_response",
    "structured_output_validation_failed",
    "provider_internal_error",
]

RETRYABLE_LLM_ERROR_CATEGORIES: frozenset[LlmErrorCategory] = frozenset(
    {"provider_unavailable", "timeout", "rate_limited"}
)

NON_FALLBACK_LLM_ERROR_CATEGORIES: frozenset[LlmErrorCategory] = frozenset(
    {
        "authentication_error",
        "invalid_request",
        "safety_blocked",
        "structured_output_validation_failed",
        "provider_not_configured",
    }
)


class LlmMessage(BaseModel):
    """Single chat message for LLM generation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    role: LlmMessageRole
    content: str = Field(min_length=1)


class LlmRequest(BaseModel):
    """Provider-neutral LLM generation request."""

    model_config = ConfigDict(arbitrary_types_allowed=True, str_strip_whitespace=True)

    messages: list[LlmMessage] = Field(default_factory=list)
    prompt: str | None = None
    system_instruction: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    max_output_tokens: int | None = Field(default=None, ge=1)
    response_model: type[BaseModel] | None = None
    timeout_seconds: float | None = Field(default=None, ge=0.1)
    request_id: str | None = None
    workflow_name: str | None = None
    task_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_credential_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"api_key", "openai_api_key", "gemini_api_key", "endpoint", "base_url"}
        for key in value:
            if key.lower() in forbidden:
                raise ValueError(f"metadata must not include credential key: {key}")
        return value

    def resolved_messages(self) -> list[LlmMessage]:
        """Normalize prompt/system_instruction into a message list."""
        messages = list(self.messages)
        if self.system_instruction and not any(message.role == "system" for message in messages):
            messages.insert(0, LlmMessage(role="system", content=self.system_instruction))
        if self.prompt:
            messages.append(LlmMessage(role="user", content=self.prompt))
        return messages


class LlmUsageMetadata(BaseModel):
    """Token usage metadata when available from a provider."""

    model_config = ConfigDict(str_strip_whitespace=True)

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class LlmGenerationResult(BaseModel):
    """Structured LLM generation result for workflow nodes."""

    model_config = ConfigDict(arbitrary_types_allowed=True, str_strip_whitespace=True)

    provider: str
    model: str
    text: str | None = None
    structured_output: BaseModel | dict[str, Any] | None = None
    finish_reason: str | None = None
    usage: LlmUsageMetadata | None = None
    latency_ms: float | None = Field(default=None, ge=0.0)
    retryable: bool = False
    error_category: LlmErrorCategory | None = None
    error_message: str | None = None
    provider_request_id: str | None = None
    trace_metadata: dict[str, str] = Field(default_factory=dict)
    attempted_providers: list[str] = Field(default_factory=list)
    primary_error_category: LlmErrorCategory | None = None

    @property
    def success(self) -> bool:
        if self.error_category is not None or self.error_message is not None:
            return False
        if self.structured_output is not None:
            return True
        return bool(self.text)
