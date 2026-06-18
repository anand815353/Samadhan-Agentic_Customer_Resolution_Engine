"""OpenAI LLM provider adapter (T-048)."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.core.config import Settings
from app.providers.base_llm import LlmProviderError
from app.providers.llm_schemas import (
    LlmErrorCategory,
    LlmGenerationResult,
    LlmMessage,
    LlmRequest,
    LlmUsageMetadata,
    RETRYABLE_LLM_ERROR_CATEGORIES,
)

_MAX_MODEL_NAME_LENGTH = 128
_SECRET_PATTERNS = (
    re.compile(r"api\s*[_-]?\s*key", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"bearer\s+", re.IGNORECASE),
)


@dataclass(frozen=True)
class OpenAIRawResult:
    """Normalized OpenAI SDK response for adapter tests and parsing."""

    text: str | None = None
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    response_id: str | None = None
    blocked: bool = False
    block_message: str | None = None


class OpenAILlmProvider:
    """OpenAI chat completions text generation via openai SDK."""

    provider_name = "openai"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model_name = settings.openai_model

    def is_configured(self) -> bool:
        return bool(self._settings.openai_api_key.get_secret_value().strip())

    async def generate(self, request: LlmRequest) -> LlmGenerationResult:
        started = time.perf_counter()

        messages = request.resolved_messages()
        if not messages:
            return self._error_result(
                request,
                category="invalid_request",
                message="at least one message or prompt is required",
                retryable=False,
                latency_ms=self._elapsed_ms(started),
            )

        if not self.is_configured():
            return self._error_result(
                request,
                category="provider_not_configured",
                message="OPENAI_API_KEY not configured",
                retryable=False,
                latency_ms=self._elapsed_ms(started),
            )

        try:
            model_name = self._validate_model()
            api_key = self._validate_config()
        except LlmProviderError as exc:
            category = exc.category or "invalid_request"
            return self._error_result(
                request,
                category=category,  # type: ignore[arg-type]
                message=exc.message,
                retryable=exc.retryable,
                latency_ms=self._elapsed_ms(started),
            )

        prepared = self._prepare_request(request)
        timeout = prepared.timeout_seconds or self._settings.llm_request_timeout_seconds

        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(self._generate_sync, api_key, model_name, prepared),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return self._error_result(
                request,
                category="timeout",
                message="OpenAI request timed out",
                retryable=True,
                latency_ms=self._elapsed_ms(started),
                model_name=model_name,
            )
        except Exception as exc:  # noqa: BLE001 — controlled provider boundary
            category, retryable, message = _map_openai_exception(exc)
            return self._error_result(
                request,
                category=category,
                message=message,
                retryable=retryable,
                latency_ms=self._elapsed_ms(started),
                model_name=model_name,
            )

        if raw.blocked:
            return self._error_result(
                request,
                category="safety_blocked",
                message=raw.block_message or "OpenAI blocked the response for safety reasons",
                retryable=False,
                latency_ms=self._elapsed_ms(started),
                model_name=model_name,
            )

        finish_reason = (raw.finish_reason or "").lower()
        if finish_reason == "content_filter":
            return self._error_result(
                request,
                category="safety_blocked",
                message="OpenAI blocked the response for safety reasons",
                retryable=False,
                latency_ms=self._elapsed_ms(started),
                model_name=model_name,
            )

        if not raw.text:
            return self._error_result(
                request,
                category="malformed_response",
                message="OpenAI returned an empty response",
                retryable=False,
                latency_ms=self._elapsed_ms(started),
                model_name=model_name,
            )

        usage = None
        if (
            raw.input_tokens is not None
            or raw.output_tokens is not None
            or raw.total_tokens is not None
        ):
            usage = LlmUsageMetadata(
                input_tokens=raw.input_tokens,
                output_tokens=raw.output_tokens,
                total_tokens=raw.total_tokens,
            )

        if prepared.response_model is not None:
            return self._structured_result(
                request,
                raw=raw,
                model_name=model_name,
                usage=usage,
                latency_ms=self._elapsed_ms(started),
            )

        return LlmGenerationResult(
            provider=self.provider_name,
            model=model_name,
            text=raw.text,
            finish_reason=raw.finish_reason,
            usage=usage,
            latency_ms=self._elapsed_ms(started),
            retryable=False,
            provider_request_id=request.request_id,
            trace_metadata=_trace_metadata(raw),
        )

    def _structured_result(
        self,
        request: LlmRequest,
        *,
        raw: OpenAIRawResult,
        model_name: str,
        usage: LlmUsageMetadata | None,
        latency_ms: float,
    ) -> LlmGenerationResult:
        assert request.response_model is not None
        try:
            parsed = json.loads(raw.text or "")
        except json.JSONDecodeError:
            return self._error_result(
                request,
                category="malformed_response",
                message="OpenAI returned malformed JSON",
                retryable=False,
                latency_ms=latency_ms,
                model_name=model_name,
            )

        try:
            structured = request.response_model.model_validate(parsed)
        except ValidationError:
            return self._error_result(
                request,
                category="structured_output_validation_failed",
                message="structured output did not match schema",
                retryable=False,
                latency_ms=latency_ms,
                model_name=model_name,
            )

        return LlmGenerationResult(
            provider=self.provider_name,
            model=model_name,
            text=raw.text,
            structured_output=structured,
            finish_reason=raw.finish_reason,
            usage=usage,
            latency_ms=latency_ms,
            retryable=False,
            provider_request_id=request.request_id,
            trace_metadata=_trace_metadata(raw),
        )

    def _validate_config(self) -> str:
        api_key = self._settings.openai_api_key.get_secret_value().strip()
        if not api_key:
            raise LlmProviderError(
                "OPENAI_API_KEY not configured",
                category="provider_not_configured",
            )
        return api_key

    def _validate_model(self) -> str:
        model_name = self.model_name.strip()
        if not model_name:
            raise LlmProviderError(
                "OPENAI_MODEL is not configured",
                category="invalid_request",
            )
        if len(model_name) > _MAX_MODEL_NAME_LENGTH:
            raise LlmProviderError(
                "OPENAI_MODEL name is too long",
                category="invalid_request",
            )
        return model_name

    def _prepare_request(self, request: LlmRequest) -> LlmRequest:
        requested_tokens = request.max_output_tokens or self._settings.max_output_tokens
        capped_tokens = min(requested_tokens, self._settings.max_output_tokens)
        timeout = request.timeout_seconds or self._settings.llm_request_timeout_seconds
        timeout = min(timeout, self._settings.llm_request_timeout_seconds)
        return request.model_copy(
            update={
                "max_output_tokens": capped_tokens,
                "timeout_seconds": timeout,
            }
        )

    def _generate_sync(
        self,
        api_key: str,
        model_name: str,
        request: LlmRequest,
    ) -> OpenAIRawResult:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        messages = _build_messages(request.resolved_messages())

        create_kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "max_tokens": request.max_output_tokens,
        }
        if request.temperature is not None:
            create_kwargs["temperature"] = request.temperature
        if request.response_model is not None:
            schema_name = request.response_model.__name__
            create_kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": request.response_model.model_json_schema(),
                    "strict": True,
                },
            }

        response = client.chat.completions.create(**create_kwargs)
        return _parse_sdk_response(response)

    def _error_result(
        self,
        request: LlmRequest,
        *,
        category: LlmErrorCategory,
        message: str,
        retryable: bool,
        latency_ms: float,
        model_name: str | None = None,
    ) -> LlmGenerationResult:
        return LlmGenerationResult(
            provider=self.provider_name,
            model=model_name or self.model_name,
            error_category=category,
            error_message=_safe_error_message(message),
            retryable=retryable,
            latency_ms=latency_ms,
            provider_request_id=request.request_id,
        )

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return round((time.perf_counter() - started) * 1000.0, 2)


def _build_messages(messages: list[LlmMessage]) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in messages]


def _parse_sdk_response(response: Any) -> OpenAIRawResult:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return OpenAIRawResult(
            response_id=getattr(response, "id", None),
        )

    choice = choices[0]
    message = getattr(choice, "message", None)
    refusal = getattr(message, "refusal", None) if message is not None else None
    if refusal:
        return OpenAIRawResult(
            blocked=True,
            block_message="OpenAI refused the response",
            response_id=getattr(response, "id", None),
        )

    text = getattr(message, "content", None) if message is not None else None
    finish_reason = getattr(choice, "finish_reason", None)
    if finish_reason is not None:
        finish_reason = str(finish_reason)

    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
    output_tokens = getattr(usage, "completion_tokens", None) if usage else None
    total_tokens = getattr(usage, "total_tokens", None) if usage else None

    return OpenAIRawResult(
        text=text,
        finish_reason=finish_reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        response_id=getattr(response, "id", None),
    )


def _trace_metadata(raw: OpenAIRawResult) -> dict[str, str]:
    metadata: dict[str, str] = {}
    if raw.response_id:
        metadata["openai_response_id"] = raw.response_id
    return metadata


def _safe_error_message(message: str) -> str:
    lowered = message.lower()
    for pattern in _SECRET_PATTERNS:
        if pattern.search(lowered):
            return "OpenAI request failed due to configuration error"
    if "traceback" in lowered:
        return "OpenAI request failed"
    return message[:240]


def _map_openai_exception(exc: Exception) -> tuple[LlmErrorCategory, bool, str]:
    from openai import (
        APIConnectionError,
        APIStatusError,
        APITimeoutError,
        AuthenticationError,
        BadRequestError,
        ContentFilterFinishReasonError,
        InternalServerError,
        RateLimitError,
    )

    if isinstance(exc, LlmProviderError):
        category = exc.category or "provider_internal_error"
        retryable = category in RETRYABLE_LLM_ERROR_CATEGORIES
        return category, retryable, exc.message  # type: ignore[return-value]

    if isinstance(exc, AuthenticationError):
        return "authentication_error", False, _safe_error_message(str(exc))

    if isinstance(exc, BadRequestError):
        return "invalid_request", False, _safe_error_message(str(exc))

    if isinstance(exc, RateLimitError):
        return "rate_limited", True, "OpenAI rate limit exceeded"

    if isinstance(exc, APITimeoutError):
        return "timeout", True, "OpenAI request timed out"

    if isinstance(exc, APIConnectionError):
        return "provider_unavailable", True, "OpenAI service is temporarily unavailable"

    if isinstance(exc, InternalServerError):
        return "provider_unavailable", True, "OpenAI service is temporarily unavailable"

    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", 0) or 0
        if status == 429:
            return "rate_limited", True, "OpenAI rate limit exceeded"
        if 500 <= status < 600:
            return "provider_unavailable", True, "OpenAI service is temporarily unavailable"
        if status in {401, 403}:
            return "authentication_error", False, _safe_error_message(str(exc))
        if status == 400:
            return "invalid_request", False, _safe_error_message(str(exc))
        return "provider_internal_error", False, _safe_error_message(str(exc))

    if isinstance(exc, ContentFilterFinishReasonError):
        return "safety_blocked", False, "OpenAI blocked the response for safety reasons"

    message = str(exc)
    lowered = message.lower()
    if "timeout" in lowered:
        return "timeout", True, "OpenAI request timed out"
    if "content_filter" in lowered or "safety" in lowered:
        return "safety_blocked", False, "OpenAI blocked the response for safety reasons"
    if "connection" in lowered or "unavailable" in lowered:
        return "provider_unavailable", True, "OpenAI service is temporarily unavailable"

    return "provider_internal_error", False, _safe_error_message(message)
