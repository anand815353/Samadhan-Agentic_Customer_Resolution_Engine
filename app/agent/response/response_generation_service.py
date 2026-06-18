"""Customer response generation orchestration (T-061)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from app.agent.response.llm_schema import LlmCustomerResponseOutput
from app.agent.response.prompt_context import SafePromptContext, build_safe_prompt_context
from app.agent.response.response_normalizer import normalize_response_text
from app.agent.response.response_types import RESPONSE_PROMPT_VERSION
from app.agent.response.response_prompt import (
    build_response_system_prompt,
    build_response_user_prompt,
)
from app.agent.response.response_safety import validate_response_safety
from app.agent.response.response_templates import render_deterministic_response
from app.agent.response.response_types import (
    RESPONSE_LLM_MAX_OUTPUT_TOKENS,
    ResponseGenerationResult,
)
from app.agent.response.trusted_facts import TrustedResponseFacts, build_trusted_response_facts
from app.agent.state import AgentState
from app.providers.base_llm import get_llm_provider
from app.providers.llm_schemas import LlmRequest

if TYPE_CHECKING:
    from app.agent.response_deps import ResponseDeps

logger = logging.getLogger("samadhan.agent")


def _llm_provider_available(settings) -> bool:
    if settings.llm_provider == "fake":
        return True
    provider = get_llm_provider(settings)
    return provider.is_configured()


def _extract_llm_text(result) -> str | None:
    if result.structured_output is not None:
        if isinstance(result.structured_output, LlmCustomerResponseOutput):
            return result.structured_output.response_text
        try:
            parsed = LlmCustomerResponseOutput.model_validate(result.structured_output)
            return parsed.response_text
        except ValidationError:
            if isinstance(result.structured_output, dict):
                text = result.structured_output.get("response_text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
    if result.text and result.text.strip():
        return result.text.strip()
    return None


def _referenced_source_ids(facts: TrustedResponseFacts) -> tuple[str, ...]:
    return tuple(snippet.document_id for snippet in facts.policy_snippets)


def _referenced_service_request_ids(facts: TrustedResponseFacts) -> tuple[str, ...]:
    if facts.service_request_id:
        return (facts.service_request_id,)
    return ()


def _build_result(
    *,
    text: str,
    facts: TrustedResponseFacts,
    generation_source: str,
    safety_status: str,
    fallback_reason: str | None,
) -> ResponseGenerationResult:
    normalized = normalize_response_text(text)
    disclaimer = "mock demo" in normalized.lower() or "simulated" in normalized.lower()
    return ResponseGenerationResult(
        response_text=normalized,
        generation_source=generation_source,  # type: ignore[arg-type]
        prompt_version=RESPONSE_PROMPT_VERSION,
        safety_status=safety_status,  # type: ignore[arg-type]
        referenced_ticket_id=facts.ticket_id,
        referenced_service_request_ids=_referenced_service_request_ids(facts),
        referenced_source_ids=_referenced_source_ids(facts),
        fallback_reason=fallback_reason,
        mock_disclaimer_included=disclaimer or facts.mock_disclaimer_required,
    )


def _template_fallback(
    facts: TrustedResponseFacts,
    *,
    fallback_reason: str | None,
) -> ResponseGenerationResult:
    text = render_deterministic_response(facts)
    safety = validate_response_safety(text, facts)
    if not safety.passed:
        raise ValueError(safety.reason or "deterministic template failed safety validation")
    return _build_result(
        text=text,
        facts=facts,
        generation_source="deterministic_template",
        safety_status="fallback_used" if fallback_reason else "passed",
        fallback_reason=fallback_reason,
    )


class ResponseGenerationService:
    """Generate validated customer-safe responses from resolution plans."""

    def __init__(self, deps: ResponseDeps) -> None:
        self._deps = deps

    async def generate(self, state: AgentState) -> ResponseGenerationResult:
        facts = build_trusted_response_facts(state)
        context = build_safe_prompt_context(facts)

        if self._deps.policy_version != RESPONSE_PROMPT_VERSION:
            raise ValueError("response prompt policy version mismatch")

        settings = self._deps.settings
        if not _llm_provider_available(settings):
            return _template_fallback(facts, fallback_reason="LLM provider not configured")

        try:
            llm_result = await self._deps.llm_service.generate(
                self._build_llm_request(state, context),
            )
        except asyncio.CancelledError:
            raise

        if not llm_result.success:
            return _template_fallback(
                facts,
                fallback_reason=llm_result.error_category or "LLM generation failed",
            )

        candidate = _extract_llm_text(llm_result)
        if candidate is None:
            return _template_fallback(facts, fallback_reason="empty LLM response")

        normalized = normalize_response_text(candidate)
        safety = validate_response_safety(normalized, facts)
        if not safety.passed:
            return _template_fallback(
                facts,
                fallback_reason=safety.reason or "response failed safety validation",
            )

        logger.info(
            "response generated via LLM workflow_id=%s ticket_id=%s response_type=%s",
            state.workflow_id,
            facts.ticket_id,
            facts.customer_response_type,
        )
        return _build_result(
            text=normalized,
            facts=facts,
            generation_source="llm",
            safety_status="passed",
            fallback_reason=None,
        )

    def _build_llm_request(self, state: AgentState, context: SafePromptContext) -> LlmRequest:
        max_tokens = min(
            self._deps.settings.max_output_tokens,
            RESPONSE_LLM_MAX_OUTPUT_TOKENS,
        )
        return LlmRequest(
            system_instruction=build_response_system_prompt(),
            prompt=build_response_user_prompt(context),
            response_model=LlmCustomerResponseOutput,
            temperature=0.0,
            max_output_tokens=max_tokens,
            workflow_name="samadhan_agent",
            task_name="response_generator",
            request_id=state.workflow_id,
        )
