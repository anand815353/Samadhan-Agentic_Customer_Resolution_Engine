"""Gemini API LLM provider adapter (T-047)."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

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
)


@dataclass(frozen=True)
class GeminiRawResult:
    """Normalized Gemini SDK response for adapter tests and parsing."""

    text: str | None = None
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    response_id: str | None = None
    blocked: bool = False
    block_message: str | None = None


class GeminiLlmProvider:
    """Gemini API text generation via google-genai SDK."""

    provider_name = "gemini_api"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model_name = settings.gemini_model

    def is_configured(self) -> bool:
        return bool(self._settings.gemini_api_key.get_secret_value().strip())

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
                message="GEMINI_API_KEY not configured",
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
                message="Gemini request timed out",
                retryable=True,
                latency_ms=self._elapsed_ms(started),
                model_name=model_name,
            )
        except Exception as exc:  # noqa: BLE001 — controlled provider boundary
            category, retryable, message = _map_gemini_exception(exc)
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
                message=raw.block_message or "Gemini blocked the response for safety reasons",
                retryable=False,
                latency_ms=self._elapsed_ms(started),
                model_name=model_name,
            )

        finish_reason = (raw.finish_reason or "").upper()
        if finish_reason in {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"}:
            return self._error_result(
                request,
                category="safety_blocked",
                message="Gemini blocked the response for safety reasons",
                retryable=False,
                latency_ms=self._elapsed_ms(started),
                model_name=model_name,
            )

        if not raw.text:
            return self._error_result(
                request,
                category="malformed_response",
                message="Gemini returned an empty response",
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
        raw: GeminiRawResult,
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
                message="Gemini returned malformed JSON",
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
        api_key = self._settings.gemini_api_key.get_secret_value().strip()
        if not api_key:
            raise LlmProviderError(
                "GEMINI_API_KEY not configured",
                category="provider_not_configured",
            )
        return api_key

    def _validate_model(self) -> str:
        model_name = self.model_name.strip()
        if not model_name:
            raise LlmProviderError(
                "GEMINI_MODEL is not configured",
                category="invalid_request",
            )
        if len(model_name) > _MAX_MODEL_NAME_LENGTH:
            raise LlmProviderError(
                "GEMINI_MODEL name is too long",
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
    ) -> GeminiRawResult:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        messages = request.resolved_messages()
        system_instruction = _extract_system_instruction(messages)
        contents = _build_contents(messages)

        config_kwargs: dict[str, Any] = {
            "max_output_tokens": request.max_output_tokens,
        }
        if request.temperature is not None:
            config_kwargs["temperature"] = request.temperature
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if request.response_model is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = request.response_model

        config = types.GenerateContentConfig(**config_kwargs)
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
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


def _extract_system_instruction(messages: list[LlmMessage]) -> str | None:
    system_messages = [message.content for message in messages if message.role == "system"]
    if not system_messages:
        return None
    return "\n".join(system_messages)


def _build_contents(messages: list[LlmMessage]) -> list[Any]:
    from google.genai import types

    contents: list[Any] = []
    for message in messages:
        if message.role == "system":
            continue
        role = "model" if message.role == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=message.content)])
        )
    return contents


def _parse_sdk_response(response: Any) -> GeminiRawResult:
    prompt_feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(prompt_feedback, "block_reason", None)
    if block_reason is not None:
        return GeminiRawResult(
            blocked=True,
            block_message="Gemini blocked the prompt",
            response_id=getattr(response, "response_id", None),
        )

    text = getattr(response, "text", None)
    candidates = getattr(response, "candidates", None) or []
    finish_reason = None
    if candidates:
        finish_reason = getattr(candidates[0], "finish_reason", None)
        if finish_reason is not None:
            finish_reason = str(finish_reason)

    usage_meta = getattr(response, "usage_metadata", None)
    input_tokens = getattr(usage_meta, "prompt_token_count", None) if usage_meta else None
    output_tokens = (
        getattr(usage_meta, "candidates_token_count", None) if usage_meta else None
    )
    total_tokens = getattr(usage_meta, "total_token_count", None) if usage_meta else None

    return GeminiRawResult(
        text=text,
        finish_reason=finish_reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        response_id=getattr(response, "response_id", None),
    )


def _trace_metadata(raw: GeminiRawResult) -> dict[str, str]:
    metadata: dict[str, str] = {}
    if raw.response_id:
        metadata["gemini_response_id"] = raw.response_id
    return metadata


def _safe_error_message(message: str) -> str:
    lowered = message.lower()
    for pattern in _SECRET_PATTERNS:
        if pattern.search(lowered):
            return "Gemini request failed due to configuration error"
    if "traceback" in lowered:
        return "Gemini request failed"
    return message[:240]


def _map_gemini_exception(exc: Exception) -> tuple[LlmErrorCategory, bool, str]:
    from google.genai.errors import APIError, ClientError, ServerError

    if isinstance(exc, LlmProviderError):
        category = exc.category or "provider_internal_error"
        retryable = category in RETRYABLE_LLM_ERROR_CATEGORIES
        return category, retryable, exc.message  # type: ignore[return-value]

    if isinstance(exc, ClientError):
        code = getattr(exc, "code", 0) or 0
        message = getattr(exc, "message", None) or str(exc)
        if code == 401 or code == 403 or "api key" in message.lower():
            return "authentication_error", False, _safe_error_message(message)
        if code == 429 or "rate" in message.lower() or "quota" in message.lower():
            return "rate_limited", True, _safe_error_message(message)
        if code == 400:
            return "invalid_request", False, _safe_error_message(message)
        return "invalid_request", False, _safe_error_message(message)

    if isinstance(exc, ServerError):
        return "provider_unavailable", True, "Gemini service is temporarily unavailable"

    if isinstance(exc, APIError):
        code = getattr(exc, "code", 0) or 0
        if code == 429:
            return "rate_limited", True, "Gemini rate limit exceeded"
        if 500 <= code < 600:
            return "provider_unavailable", True, "Gemini service is temporarily unavailable"
        return "provider_internal_error", False, _safe_error_message(str(exc))

    message = str(exc)
    lowered = message.lower()
    if "timeout" in lowered:
        return "timeout", True, "Gemini request timed out"
    if "safety" in lowered or "blocked" in lowered:
        return "safety_blocked", False, "Gemini blocked the response for safety reasons"
    if "connection" in lowered or "unavailable" in lowered:
        return "provider_unavailable", True, "Gemini service is temporarily unavailable"

    return "provider_internal_error", False, _safe_error_message(message)
