"""Vertex AI LLM provider adapter (T-049)."""

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
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"service\s*account", re.IGNORECASE),
    re.compile(r"bearer\s+", re.IGNORECASE),
)


@dataclass(frozen=True)
class VertexRawResult:
    """Normalized Vertex AI SDK response for adapter tests and parsing."""

    text: str | None = None
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    response_id: str | None = None
    blocked: bool = False
    block_message: str | None = None


class VertexLlmProvider:
    """Vertex AI text generation via google-genai SDK (vertexai mode)."""

    provider_name = "vertex_ai"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model_name = settings.vertex_ai_model

    def is_configured(self) -> bool:
        return bool(self._settings.vertex_ai_project_id.strip())

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
                message="VERTEX_AI_PROJECT_ID not configured",
                retryable=False,
                latency_ms=self._elapsed_ms(started),
            )

        try:
            project_id = self._validate_project()
            location = self._validate_location()
            model_name = self._validate_model()
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
                asyncio.to_thread(
                    self._generate_sync,
                    project_id,
                    location,
                    model_name,
                    prepared,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return self._error_result(
                request,
                category="timeout",
                message="Vertex AI request timed out",
                retryable=True,
                latency_ms=self._elapsed_ms(started),
                model_name=model_name,
            )
        except Exception as exc:  # noqa: BLE001 — controlled provider boundary
            category, retryable, message = _map_vertex_exception(exc)
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
                message=raw.block_message or "Vertex AI blocked the response for safety reasons",
                retryable=False,
                latency_ms=self._elapsed_ms(started),
                model_name=model_name,
            )

        finish_reason = (raw.finish_reason or "").upper()
        if finish_reason in {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"}:
            return self._error_result(
                request,
                category="safety_blocked",
                message="Vertex AI blocked the response for safety reasons",
                retryable=False,
                latency_ms=self._elapsed_ms(started),
                model_name=model_name,
            )

        if not raw.text:
            return self._error_result(
                request,
                category="malformed_response",
                message="Vertex AI returned an empty response",
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
                location=location,
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
            trace_metadata=_trace_metadata(raw, location=location),
        )

    def _structured_result(
        self,
        request: LlmRequest,
        *,
        raw: VertexRawResult,
        model_name: str,
        location: str,
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
                message="Vertex AI returned malformed JSON",
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
            trace_metadata=_trace_metadata(raw, location=location),
        )

    def _validate_project(self) -> str:
        project_id = self._settings.vertex_ai_project_id.strip()
        if not project_id:
            raise LlmProviderError(
                "VERTEX_AI_PROJECT_ID not configured",
                category="provider_not_configured",
            )
        if len(project_id) > _MAX_MODEL_NAME_LENGTH:
            raise LlmProviderError(
                "VERTEX_AI_PROJECT_ID is too long",
                category="invalid_request",
            )
        return project_id

    def _validate_location(self) -> str:
        location = self._settings.vertex_ai_location.strip()
        if not location:
            raise LlmProviderError(
                "VERTEX_AI_LOCATION is not configured",
                category="invalid_request",
            )
        if len(location) > _MAX_MODEL_NAME_LENGTH:
            raise LlmProviderError(
                "VERTEX_AI_LOCATION is too long",
                category="invalid_request",
            )
        return location

    def _validate_model(self) -> str:
        model_name = self.model_name.strip()
        if not model_name:
            raise LlmProviderError(
                "VERTEX_AI_MODEL is not configured",
                category="invalid_request",
            )
        if len(model_name) > _MAX_MODEL_NAME_LENGTH:
            raise LlmProviderError(
                "VERTEX_AI_MODEL name is too long",
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
        project_id: str,
        location: str,
        model_name: str,
        request: LlmRequest,
    ) -> VertexRawResult:
        from google import genai
        from google.genai import types

        client = genai.Client(vertexai=True, project=project_id, location=location)
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


def _parse_sdk_response(response: Any) -> VertexRawResult:
    prompt_feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(prompt_feedback, "block_reason", None)
    if block_reason is not None:
        return VertexRawResult(
            blocked=True,
            block_message="Vertex AI blocked the prompt",
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

    return VertexRawResult(
        text=text,
        finish_reason=finish_reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        response_id=getattr(response, "response_id", None),
    )


def _trace_metadata(raw: VertexRawResult, *, location: str) -> dict[str, str]:
    metadata: dict[str, str] = {"vertex_location": location}
    if raw.response_id:
        metadata["vertex_response_id"] = raw.response_id
    return metadata


def _safe_error_message(message: str) -> str:
    lowered = message.lower()
    for pattern in _SECRET_PATTERNS:
        if pattern.search(lowered):
            return "Vertex AI request failed due to configuration error"
    if "traceback" in lowered:
        return "Vertex AI request failed"
    if "projects/" in lowered or "googleapis.com" in lowered:
        return "Vertex AI request failed due to configuration error"
    return message[:240]


def _map_vertex_exception(exc: Exception) -> tuple[LlmErrorCategory, bool, str]:
    from google.genai.errors import APIError, ClientError, ServerError

    if isinstance(exc, LlmProviderError):
        category = exc.category or "provider_internal_error"
        retryable = category in RETRYABLE_LLM_ERROR_CATEGORIES
        return category, retryable, exc.message  # type: ignore[return-value]

    if isinstance(exc, ClientError):
        code = getattr(exc, "code", 0) or 0
        message = getattr(exc, "message", None) or str(exc)
        lowered = message.lower()
        if code in {401, 403} or "permission" in lowered or "credential" in lowered:
            return "authentication_error", False, _safe_error_message(message)
        if code == 429 or "rate" in lowered or "quota" in lowered or "resource_exhausted" in lowered:
            return "rate_limited", True, "Vertex AI rate limit exceeded"
        if code == 404 or "not found" in lowered:
            return "invalid_request", False, "Vertex AI model or resource not found"
        if code == 400 or "invalid" in lowered or "location" in lowered:
            return "invalid_request", False, _safe_error_message(message)
        return "invalid_request", False, _safe_error_message(message)

    if isinstance(exc, ServerError):
        return "provider_unavailable", True, "Vertex AI service is temporarily unavailable"

    if isinstance(exc, APIError):
        code = getattr(exc, "code", 0) or 0
        if code == 429:
            return "rate_limited", True, "Vertex AI rate limit exceeded"
        if 500 <= code < 600:
            return "provider_unavailable", True, "Vertex AI service is temporarily unavailable"
        return "provider_internal_error", False, _safe_error_message(str(exc))

    message = str(exc)
    lowered = message.lower()
    if "timeout" in lowered:
        return "timeout", True, "Vertex AI request timed out"
    if "safety" in lowered or "blocked" in lowered:
        return "safety_blocked", False, "Vertex AI blocked the response for safety reasons"
    if "connection" in lowered or "unavailable" in lowered:
        return "provider_unavailable", True, "Vertex AI service is temporarily unavailable"
    if "permission" in lowered or "credential" in lowered or "unauthenticated" in lowered:
        return "authentication_error", False, _safe_error_message(message)
    if "quota" in lowered or "resource_exhausted" in lowered:
        return "rate_limited", True, "Vertex AI rate limit exceeded"

    return "provider_internal_error", False, _safe_error_message(message)
