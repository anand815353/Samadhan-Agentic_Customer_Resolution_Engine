"""LLM generation orchestration with fallback and safe logging (T-046)."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.core.config import LlmProviderName, Settings, get_settings
from app.providers.base_llm import LlmProvider, get_llm_provider
from app.providers.llm_schemas import (
    NON_FALLBACK_LLM_ERROR_CATEGORIES,
    LlmGenerationResult,
    LlmRequest,
)

logger = logging.getLogger("samadhan.llm")


class LlmGenerationService:
    """High-level LLM generation with token caps, fallback, and safe logging."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(self, request: LlmRequest) -> LlmGenerationResult:
        prepared = self._prepare_request(request)
        attempted: list[str] = []
        primary_error_category = None
        last_result: LlmGenerationResult | None = None

        provider_plan = self._provider_plan()
        max_attempts = min(len(provider_plan), self._settings.llm_max_provider_attempts)

        for index, provider_name in enumerate(provider_plan[:max_attempts]):
            provider = get_llm_provider(self._settings, provider_name=provider_name)
            started = time.perf_counter()
            result = await provider.generate(prepared)
            result = result.model_copy(
                update={
                    "attempted_providers": list(attempted) + [provider.provider_name],
                    "primary_error_category": primary_error_category,
                }
            )
            attempted.append(provider.provider_name)
            self._log_attempt(prepared, result, attempt=index + 1)

            if result.success:
                return result

            if primary_error_category is None and result.error_category is not None:
                primary_error_category = result.error_category

            last_result = result
            if not self._should_try_fallback(result, index=index, plan_size=len(provider_plan)):
                break

        assert last_result is not None
        return last_result.model_copy(
            update={
                "attempted_providers": attempted,
                "primary_error_category": primary_error_category,
            }
        )

    def _prepare_request(self, request: LlmRequest) -> LlmRequest:
        capped_tokens = request.max_output_tokens or self._settings.max_output_tokens
        capped_tokens = min(capped_tokens, self._settings.max_output_tokens)
        timeout = request.timeout_seconds or self._settings.llm_request_timeout_seconds
        timeout = min(timeout, self._settings.llm_request_timeout_seconds)
        return request.model_copy(
            update={
                "max_output_tokens": capped_tokens,
                "timeout_seconds": timeout,
            }
        )

    def _provider_plan(self) -> list[LlmProviderName]:
        primary = self._settings.llm_provider
        plan: list[LlmProviderName] = [primary]
        fallback = self._settings.llm_fallback_provider
        if (
            self._settings.llm_fallback_enabled
            and fallback is not None
            and fallback != primary
        ):
            plan.append(fallback)
        return plan

    def _should_try_fallback(
        self,
        result: LlmGenerationResult,
        *,
        index: int,
        plan_size: int,
    ) -> bool:
        if index >= plan_size - 1:
            return False
        if not self._settings.llm_fallback_enabled:
            return False
        if result.error_category in NON_FALLBACK_LLM_ERROR_CATEGORIES:
            return False
        return result.retryable

    def _log_attempt(
        self,
        request: LlmRequest,
        result: LlmGenerationResult,
        *,
        attempt: int,
    ) -> None:
        messages = request.resolved_messages()
        prompt_chars = sum(len(message.content) for message in messages)
        extra: dict[str, Any] = {
            "provider": result.provider,
            "model": result.model,
            "request_id": request.request_id,
            "workflow_name": request.workflow_name,
            "task_name": request.task_name,
            "success": result.success,
            "error_category": result.error_category,
            "latency_ms": result.latency_ms,
            "attempt": attempt,
            "message_count": len(messages),
            "prompt_chars": prompt_chars,
        }
        if result.success:
            logger.info("LLM generation completed", extra=extra)
        else:
            logger.warning("LLM generation failed", extra=extra)


def get_llm_generation_service(settings: Settings | None = None) -> LlmGenerationService:
    """Return the configured LLM generation service."""
    return LlmGenerationService(settings or get_settings())
