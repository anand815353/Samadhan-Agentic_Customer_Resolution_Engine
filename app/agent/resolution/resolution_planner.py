"""Deterministic resolution planning orchestrator (T-060)."""

from __future__ import annotations

from app.agent.exceptions import ResolutionPlannerValidationError
from app.agent.resolution.escalation_policy import compute_escalation
from app.agent.resolution.intent_resolution_policy import resolve_intent_metadata
from app.agent.resolution.resolution_types import MANDATORY_ESCALATE_INTENTS
from app.agent.resolution.ticket_status_policy import select_ticket_status
from app.agent.resolution.tool_outcome_collector import (
    collect_tool_outcomes,
    has_service_request_created,
    primary_service_request_id,
)
from app.agent.state import AgentState, ResolutionPlan
from app.tickets.constants import ALL_TICKET_INTENTS


def _validate_prerequisites(state: AgentState) -> None:
    if state.intent_classification is None:
        raise ResolutionPlannerValidationError(
            "intent classification is required before resolution planning",
        )
    if state.risk_routing is None:
        raise ResolutionPlannerValidationError(
            "risk routing is required before resolution planning",
        )
    if state.risk_routing.ticket_class is None:
        raise ResolutionPlannerValidationError(
            "ticket class is required before resolution planning",
        )
    if state.guardrail is None:
        raise ResolutionPlannerValidationError(
            "guardrail decision is required before resolution planning",
        )
    intent = state.intent_classification.intent
    if intent not in ALL_TICKET_INTENTS:
        raise ResolutionPlannerValidationError("unsupported intent for resolution planning")


def plan_resolution(state: AgentState) -> ResolutionPlan:
    """Build a validated structured resolution plan from workflow state."""
    _validate_prerequisites(state)
    intent = state.intent_classification.intent  # type: ignore[union-attr]
    risk = state.risk_routing  # type: ignore[union-attr]
    guardrail = state.guardrail
    assert guardrail is not None
    assert risk.ticket_class is not None

    outcomes = collect_tool_outcomes(
        state.tool_steps,
        high_risk_intents=MANDATORY_ESCALATE_INTENTS | {"bureau_reporting_issue", "unknown"},
        intent=intent,
    )
    escalation_required, escalation_reason = compute_escalation(
        state,
        guardrail=guardrail,
        outcomes=outcomes,
    )
    metadata = resolve_intent_metadata(
        state,
        guardrail=guardrail,
        escalation_required=escalation_required,
        outcomes=outcomes,
    )
    primary_sr = primary_service_request_id(outcomes)
    ticket_status = select_ticket_status(
        intent=intent,
        ticket_class=risk.ticket_class,
        guardrail=guardrail,
        escalation_required=escalation_required,
        outcomes=outcomes,
        primary_sr_id=primary_sr,
    )

    if (
        ticket_status == "service_requested"
        and risk.ticket_class == "tier_1_service_request"
        and has_service_request_created(outcomes)
        and primary_sr is None
    ):
        ticket_status = "failed"
        metadata = resolve_intent_metadata(
            state,
            guardrail=guardrail,
            escalation_required=True,
            outcomes=outcomes,
        )
        escalation_required = True
        if escalation_reason is None:
            escalation_reason = "Required service request ID was not returned safely."

    plan = ResolutionPlan(
        intent=intent,
        risk_level=risk.risk_level,
        priority=risk.priority,
        ticket_class=risk.ticket_class,
        customer_action=metadata.customer_action,
        system_action=metadata.system_action,
        tool_actions=list(outcomes.tool_actions),
        escalation_required=escalation_required,
        escalation_reason=escalation_reason,
        customer_response_type=metadata.customer_response_type,
        service_request_id=primary_sr,
        ticket_status=ticket_status,
    )
    return ResolutionPlan.model_validate(plan.model_dump(mode="json"))
