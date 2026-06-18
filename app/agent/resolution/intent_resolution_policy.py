"""Per-intent customer/system/response-type resolution metadata (T-060)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.resolution.resolution_types import (
    CustomerAction,
    CustomerResponseType,
    SystemAction,
)
from app.agent.resolution.tool_outcome_collector import (
    ToolOutcomeSummary,
    has_document_completed,
    has_service_request_created,
)
from app.agent.state import AgentState, GuardrailState


@dataclass(frozen=True)
class IntentResolutionMetadata:
    customer_action: CustomerAction
    system_action: SystemAction
    customer_response_type: CustomerResponseType


def has_approved_policy_grounding(state: AgentState) -> bool:
    """Return True when approved policy context is available for FAQ responses."""
    if state.retrieval is not None and state.retrieval.result is not None:
        result = state.retrieval.result
        if not result.unavailable and result.chunks and state.retrieval.source_policy_ids:
            return True

    for step in state.tool_steps:
        if step.status != "completed" or step.tool_output is None:
            continue
        output = step.tool_output
        if output.success and output.action_taken == "policy_chunks_retrieved":
            return True
    return False


def _fraud_metadata(outcomes: ToolOutcomeSummary) -> IntentResolutionMetadata:
    if any(action == "fraud_case_created" for action in outcomes.tool_actions):
        return IntentResolutionMetadata(
            customer_action="wait_for_support_agent",
            system_action="mock_fraud_action_recorded",
            customer_response_type="explain_and_escalate",
        )
    return IntentResolutionMetadata(
        customer_action="wait_for_support_agent",
        system_action="prepare_human_escalation",
        customer_response_type="explain_and_escalate",
    )


def resolve_intent_metadata(
    state: AgentState,
    *,
    guardrail: GuardrailState,
    escalation_required: bool,
    outcomes: ToolOutcomeSummary,
) -> IntentResolutionMetadata:
    """Return deterministic customer/system/response metadata for the classified intent."""
    intent = state.intent_classification.intent  # type: ignore[union-attr]

    if guardrail.decision == "block":
        return IntentResolutionMetadata(
            customer_action="wait_for_support_agent",
            system_action="blocked_action_requires_review",
            customer_response_type="explain_and_escalate",
        )

    if guardrail.decision == "ask_follow_up" or intent == "unknown":
        return IntentResolutionMetadata(
            customer_action="provide_more_information",
            system_action="request_more_information",
            customer_response_type="request_more_information",
        )

    if escalation_required or intent in {
        "fraud_security_issue",
        "emi_payment_issue",
        "charges_refund_reversal",
    }:
        if intent == "fraud_security_issue":
            return _fraud_metadata(outcomes)
        return IntentResolutionMetadata(
            customer_action="wait_for_support_agent",
            system_action="prepare_human_escalation",
            customer_response_type="explain_and_escalate",
        )

    if intent == "policy_faq":
        if has_approved_policy_grounding(state):
            return IntentResolutionMetadata(
                customer_action="review_policy_information",
                system_action="policy_context_retrieved",
                customer_response_type="explain_policy",
            )
        return IntentResolutionMetadata(
            customer_action="contact_support_if_not_updated",
            system_action="safe_no_answer_available",
            customer_response_type="explain_no_approved_answer",
        )

    if has_document_completed(outcomes):
        return IntentResolutionMetadata(
            customer_action="check_documents_section",
            system_action="mock_document_generated",
            customer_response_type="confirm_mock_document",
        )

    if has_service_request_created(outcomes) or any(
        action in {"kyc_reupload_requested", "rm_callback_requested", "reversal_review_created"}
        for action in outcomes.tool_actions
    ):
        system_action: SystemAction = "service_request_created"
        if any(action == "reversal_review_created" for action in outcomes.tool_actions):
            system_action = "reversal_review_created"
        elif any(action == "rm_callback_requested" for action in outcomes.tool_actions):
            system_action = "mock_callback_requested"
        return IntentResolutionMetadata(
            customer_action="wait_for_service_completion",
            system_action=system_action,
            customer_response_type="confirm_service_request",
        )

    if intent == "topup_offer":
        if any(action.startswith("mock_offer_lead") for action in outcomes.tool_actions):
            return IntentResolutionMetadata(
                customer_action="decide_whether_to_proceed_with_offer",
                system_action="eligibility_checked",
                customer_response_type="explain_offer_eligibility",
            )
        return IntentResolutionMetadata(
            customer_action="no_action_required",
            system_action="eligibility_checked",
            customer_response_type="explain_offer_eligibility",
        )

    if outcomes.any_tool_failure:
        return IntentResolutionMetadata(
            customer_action="contact_support_if_not_updated",
            system_action="safe_no_answer_available",
            customer_response_type="explain_safe_failure",
        )

    return IntentResolutionMetadata(
        customer_action="no_action_required",
        system_action="information_checked",
        customer_response_type="explain_information",
    )
