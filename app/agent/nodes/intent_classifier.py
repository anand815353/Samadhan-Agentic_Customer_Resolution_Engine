"""LangGraph intent classifier node implementation (T-053)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import BaseModel

from app.agent.classification.intent_classifier_prompt import (
    INTENT_CLASSIFIER_PROMPT_VERSION,
    build_intent_classifier_system_prompt,
    build_intent_classifier_user_prompt,
)
from app.agent.classification.llm_schema import LlmIntentClassificationOutput
from app.agent.classification.rule_classifier import (
    RULE_MIN_CANDIDATE_SCORE,
    UNKNOWN_FALLBACK_CONFIDENCE,
    classify_by_rules,
)
from app.agent.classification.rule_patterns import RULE_CLASSIFIER_VERSION
from app.agent.constants import NODE_INTENT_CLASSIFIER, ClassificationSource
from app.agent.intent_classifier_deps import IntentClassifierDeps
from app.agent.nodes.base import NodeCallable
from app.agent.state import AgentState, IntentClassificationState, WorkflowError
from app.common.text_normalization import BlankMessageError, normalize_customer_message
from app.providers.base_llm import get_llm_provider
from app.providers.llm_schemas import LlmRequest
from app.tickets.constants import TicketIntent

logger = logging.getLogger("samadhan.agent")


def _resolve_normalized_message(state: AgentState) -> str | None:
    if state.normalized_message is not None:
        text = state.normalized_message.strip()
        return text or None
    try:
        return normalize_customer_message(state.customer_message)
    except BlankMessageError:
        return None


def _metadata_from_rule_result(rule_result) -> dict[str, str]:
    metadata: dict[str, str] = {
        "rule_classifier_version": RULE_CLASSIFIER_VERSION,
        "prompt_version": INTENT_CLASSIFIER_PROMPT_VERSION,
    }
    if rule_result.matched_rule_ids:
        metadata["matched_rule_ids"] = ",".join(rule_result.matched_rule_ids)
    if rule_result.candidates:
        metadata["candidate_intents"] = ",".join(
            f"{intent}:{score:.2f}"
            for intent, score in rule_result.candidates.items()
        )
        ranked = list(rule_result.candidates.items())
        if len(ranked) > 1:
            metadata["runner_up_intent"] = ranked[1][0]
            metadata["runner_up_score"] = f"{ranked[1][1]:.2f}"
    return metadata


def _unknown_classification(
    *,
    state: AgentState,
    reason: str,
    metadata: dict[str, str],
    workflow_errors: list[WorkflowError] | None = None,
) -> dict[str, Any]:
    errors = list(state.workflow_errors)
    if workflow_errors:
        errors.extend(workflow_errors)
    return {
        "intent_classification": IntentClassificationState(
            intent="unknown",
            confidence=UNKNOWN_FALLBACK_CONFIDENCE,
            source="rule",
            reason=reason,
            metadata=metadata,
        ),
        "workflow_errors": errors,
    }


def _llm_provider_available(settings) -> bool:
    if settings.llm_provider == "fake":
        return True
    provider = get_llm_provider(settings)
    return provider.is_configured()


def _classification_source_for_llm(rule_result, *, llm_intent: TicketIntent) -> ClassificationSource:
    has_rule_candidates = any(
        score >= RULE_MIN_CANDIDATE_SCORE for score in rule_result.candidates.values()
    )
    if has_rule_candidates and llm_intent in rule_result.candidates:
        return "hybrid"
    if has_rule_candidates:
        return "hybrid"
    return "llm"


class IntentClassifierNode:
    """Classify customer intent using rules first with optional LLM fallback."""

    def __init__(self, deps: IntentClassifierDeps) -> None:
        self._deps = deps

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        normalized_message = _resolve_normalized_message(state)
        if not normalized_message:
            metadata = {
                "rule_classifier_version": RULE_CLASSIFIER_VERSION,
                "prompt_version": INTENT_CLASSIFIER_PROMPT_VERSION,
            }
            return _unknown_classification(
                state=state,
                reason="missing or blank normalized message",
                metadata=metadata,
                workflow_errors=[
                    WorkflowError(
                        code="missing_context",
                        message="intent classification requires a normalized customer message",
                        node=NODE_INTENT_CLASSIFIER,
                        recoverable=False,
                    )
                ],
            )

        rule_result = classify_by_rules(normalized_message, settings=self._deps.settings)
        metadata = _metadata_from_rule_result(rule_result)

        if rule_result.accepted_by_threshold:
            logger.info(
                "intent classified by rules workflow_id=%s intent=%s confidence=%.2f",
                state.workflow_id,
                rule_result.intent,
                rule_result.confidence,
            )
            return {
                "normalized_message": normalized_message,
                "intent_classification": IntentClassificationState(
                    intent=rule_result.intent,
                    confidence=rule_result.confidence,
                    source="rule",
                    reason=rule_result.reason,
                    metadata=metadata,
                ),
            }

        settings = self._deps.settings
        if not settings.intent_classifier_llm_fallback_enabled or not _llm_provider_available(settings):
            metadata["llm_fallback_skipped"] = "true"
            logger.info(
                "intent classifier skipped LLM fallback workflow_id=%s top_intent=%s",
                state.workflow_id,
                rule_result.intent,
            )
            return _unknown_classification(
                state=state,
                reason="insufficient rule confidence; LLM fallback unavailable",
                metadata=metadata,
            )

        metadata["llm_fallback_attempted"] = "true"
        try:
            llm_result = await self._deps.llm_service.generate(
                LlmRequest(
                    system_instruction=build_intent_classifier_system_prompt(),
                    prompt=build_intent_classifier_user_prompt(normalized_message),
                    response_model=LlmIntentClassificationOutput,
                    temperature=0.0,
                    max_output_tokens=128,
                    workflow_name="samadhan_agent",
                    task_name="intent_classifier",
                    request_id=state.workflow_id,
                )
            )
        except asyncio.CancelledError:
            raise

        if not llm_result.success or llm_result.structured_output is None:
            logger.warning(
                "intent classifier LLM fallback failed workflow_id=%s category=%s",
                state.workflow_id,
                llm_result.error_category,
            )
            return _unknown_classification(
                state=state,
                reason="LLM fallback failed; classified as unknown",
                metadata=metadata,
                workflow_errors=[
                    WorkflowError(
                        code="llm_unavailable",
                        message="intent classifier LLM fallback failed",
                        node=NODE_INTENT_CLASSIFIER,
                        recoverable=True,
                    )
                ],
            )

        structured = llm_result.structured_output
        try:
            if isinstance(structured, LlmIntentClassificationOutput):
                parsed = structured
            elif isinstance(structured, dict):
                parsed = LlmIntentClassificationOutput.model_validate(structured)
            elif isinstance(structured, BaseModel):
                parsed = LlmIntentClassificationOutput.model_validate(structured.model_dump())
            else:
                raise TypeError("unsupported structured output type")
        except Exception:
            return _unknown_classification(
                state=state,
                reason="LLM structured output validation failed",
                metadata=metadata,
                workflow_errors=[
                    WorkflowError(
                        code="validation_failed",
                        message="intent classifier rejected LLM structured output",
                        node=NODE_INTENT_CLASSIFIER,
                        recoverable=True,
                    )
                ],
            )

        if parsed.confidence < settings.intent_classifier_min_llm_confidence:
            return _unknown_classification(
                state=state,
                reason="LLM confidence below acceptance threshold",
                metadata=metadata,
            )

        source = _classification_source_for_llm(rule_result, llm_intent=parsed.intent)
        reason = parsed.reason or f"llm classification: {parsed.intent}"
        logger.info(
            "intent classified with LLM workflow_id=%s intent=%s source=%s confidence=%.2f",
            state.workflow_id,
            parsed.intent,
            source,
            parsed.confidence,
        )
        return {
            "normalized_message": normalized_message,
            "intent_classification": IntentClassificationState(
                intent=parsed.intent,
                confidence=parsed.confidence,
                source=source,
                reason=reason[:200] if reason else None,
                metadata=metadata,
            ),
        }


def build_intent_classifier_node(deps: IntentClassifierDeps) -> NodeCallable:
    """Return an intent classifier node callable bound to dependencies."""
    node = IntentClassifierNode(deps)

    async def intent_classifier_node(state: AgentState) -> dict[str, Any]:
        return await node(state)

    return intent_classifier_node


# Registry stub; build_default_registry replaces with build_intent_classifier_node(...).
from app.agent.nodes.base import passthrough_node as intent_classifier_node  # noqa: E402

__all__ = ["IntentClassifierNode", "build_intent_classifier_node", "intent_classifier_node"]
