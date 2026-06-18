"""Deterministic fake LLM provider for tests and local no-key mode (T-046)."""

from __future__ import annotations

import hashlib
import json
import time
import typing
from typing import Any, get_args, get_origin, get_type_hints

from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefined

from app.core.config import Settings
from app.providers.llm_schemas import (
    LlmErrorCategory,
    LlmGenerationResult,
    LlmRequest,
    LlmUsageMetadata,
    RETRYABLE_LLM_ERROR_CATEGORIES,
)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _deterministic_text(messages_text: str) -> str:
    digest = hashlib.sha256(messages_text.encode("utf-8")).hexdigest()[:16]
    return f"FAKE_LLM:{digest}"


def _build_fake_structured_payload(model: type[BaseModel]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    hints = get_type_hints(model)
    for name, field in model.model_fields.items():
        if field.default is not PydanticUndefined:
            payload[name] = field.default
            continue
        if field.default_factory is not None:
            payload[name] = field.default_factory()  # type: ignore[misc]
            continue

        annotation = hints.get(name, field.annotation)
        origin = get_origin(annotation)
        if origin is typing.Literal:
            payload[name] = get_args(annotation)[0]
            continue
        if annotation is str:
            payload[name] = f"fake_{name}"
        elif annotation is int:
            payload[name] = 1
        elif annotation is float:
            payload[name] = 0.5
        elif annotation is bool:
            payload[name] = False
        elif origin is list:
            payload[name] = []
        else:
            payload[name] = f"fake_{name}"
    return payload


class FakeLlmProvider:
    """Hash-based LLM provider with no external dependencies."""

    provider_name = "fake"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model_name = "fake-llm-v1"

    def is_configured(self) -> bool:
        return True

    async def generate(self, request: LlmRequest) -> LlmGenerationResult:
        started = time.perf_counter()
        messages = request.resolved_messages()
        if not messages:
            return self._failure(
                category="invalid_request",
                message="at least one message or prompt is required",
                retryable=False,
                latency_ms=self._elapsed_ms(started),
            )

        fake_error = request.metadata.get("fake_error_category")
        if isinstance(fake_error, str):
            category: LlmErrorCategory = fake_error  # type: ignore[assignment]
            retryable = category in RETRYABLE_LLM_ERROR_CATEGORIES
            return self._failure(
                category=category,
                message=f"simulated {category}",
                retryable=retryable,
                latency_ms=self._elapsed_ms(started),
            )

        combined = "\n".join(f"{message.role}:{message.content}" for message in messages)
        input_tokens = _estimate_tokens(combined)

        if request.response_model is not None:
            fake_json = request.metadata.get("fake_structured_json")
            if isinstance(fake_json, str):
                try:
                    parsed = json.loads(fake_json)
                except json.JSONDecodeError:
                    return self._failure(
                        category="malformed_response",
                        message="fake provider received malformed JSON",
                        retryable=False,
                        latency_ms=self._elapsed_ms(started),
                    )
            else:
                parsed = _build_fake_structured_payload(request.response_model)

            try:
                structured = request.response_model.model_validate(parsed)
            except ValidationError:
                return self._failure(
                    category="structured_output_validation_failed",
                    message="structured output did not match schema",
                    retryable=False,
                    latency_ms=self._elapsed_ms(started),
                )

            output_text = json.dumps(
                structured.model_dump(mode="json")
                if isinstance(structured, BaseModel)
                else structured
            )
            output_tokens = _estimate_tokens(output_text)
            return LlmGenerationResult(
                provider=self.provider_name,
                model=self.model_name,
                structured_output=structured,
                text=output_text,
                finish_reason="stop",
                usage=LlmUsageMetadata(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                ),
                latency_ms=self._elapsed_ms(started),
                retryable=False,
                provider_request_id=request.request_id,
            )

        fake_text = request.metadata.get("fake_text")
        text = fake_text if isinstance(fake_text, str) else _deterministic_text(combined)
        output_tokens = _estimate_tokens(text)
        return LlmGenerationResult(
            provider=self.provider_name,
            model=self.model_name,
            text=text,
            finish_reason="stop",
            usage=LlmUsageMetadata(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
            latency_ms=self._elapsed_ms(started),
            retryable=False,
            provider_request_id=request.request_id,
        )

    def _failure(
        self,
        *,
        category: LlmErrorCategory,
        message: str,
        retryable: bool,
        latency_ms: float,
    ) -> LlmGenerationResult:
        return LlmGenerationResult(
            provider=self.provider_name,
            model=self.model_name,
            error_category=category,
            error_message=message,
            retryable=retryable,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return round((time.perf_counter() - started) * 1000.0, 2)
