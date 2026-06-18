"""Deterministic intent guardrail policy (T-058)."""

from __future__ import annotations

from app.agent.constants import GuardrailDecision
from app.agent.guardrails.guardrail_types import (
    ACTION_CREATE_HUMAN_REVIEW_TICKET,
    GUARDRAIL_POLICY_VERSION,
    MAX_GUARDRAIL_REASON_LENGTH,
    TOOL_TO_ALLOWED_ACTIONS,
    GuardrailEvaluationResult,
)
from app.agent.guardrails.tool_plan_integrity import PlanIntegrityResult
from app.agent.planning.tool_plan_types import PLANNER_CONDITION_AFTER_BUREAU_CLOSURE_LETTER
from app.agent.risk.intent_risk_policy import LOW_INTENT_CONFIDENCE_THRESHOLD
from app.agent.state import AgentState
from app.tickets.constants import TICKET_CLASS_HUMAN_REVIEW, TICKET_CLASS_TIER_1, TicketIntent

_MANDATORY_ESCALATE_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "fraud_security_issue",
        "emi_payment_issue",
        "charges_refund_reversal",
    }
)

_TIER1_AUDIT_INTENTS: frozenset[TicketIntent] = frozenset(
    {
        "rm_redirection",
        "loan_statement_request",
        "noc_closure_certificate",
    }
)


def _informational_allowance(state: AgentState) -> tuple[GuardrailDecision, bool, str]:
    intent = state.intent_classification.intent  # type: ignore[union-attr]
    ticket_class = state.risk_routing.ticket_class  # type: ignore[union-attr]

    if intent == "loan_application_status":
        return (
            "allow_with_audit",
            False,
            "Loan status lookup may proceed with audit.",
        )

    if intent in _TIER1_AUDIT_INTENTS or ticket_class == TICKET_CLASS_TIER_1:
        return (
            "allow_with_audit",
            False,
            "Service action requires an auditable workflow record.",
        )

    return (
        "allow",
        False,
        "Planned mock tools passed guardrail checks.",
    )

_REJECTION_DISPUTE_PHRASES: tuple[str, ...] = (
    "disagree",
    "review again",
    "unfair",
    "reconsider",
)


def _message_text(state: AgentState) -> str:
    return (state.normalized_message or state.customer_message).strip().lower()


def _is_rejection_dispute(state: AgentState) -> bool:
    text = _message_text(state)
    return any(phrase in text for phrase in _REJECTION_DISPUTE_PHRASES)


def _low_confidence_escalation(state: AgentState) -> bool:
    intent_state = state.intent_classification
    assert intent_state is not None
    if intent_state.intent == "unknown":
        return False
    return intent_state.confidence < LOW_INTENT_CONFIDENCE_THRESHOLD


def _overall_decision(state: AgentState) -> tuple[GuardrailDecision, bool, str]:
    intent = state.intent_classification.intent  # type: ignore[union-attr]
    ticket_class = state.risk_routing.ticket_class  # type: ignore[union-attr]

    if intent == "unknown":
        return (
            "ask_follow_up",
            False,
            "Unknown intent requires clarification before automated tools can run.",
        )

    if intent in _MANDATORY_ESCALATE_INTENTS:
        return (
            "escalate",
            True,
            "High-risk financial or security scenario requires mandatory Human Review.",
        )

    if intent == "rejection_reason" and _is_rejection_dispute(state):
        return (
            "escalate",
            True,
            "Rejection dispute requires Human Review before further action.",
        )

    if intent == "bureau_reporting_issue":
        if ticket_class == TICKET_CLASS_HUMAN_REVIEW:
            return (
                "escalate",
                True,
                "Bureau reporting issue with Human Review routing requires escalation.",
            )
        return (
            "allow_with_audit",
            False,
            "Bureau reporting check may proceed with audit for Tier 1 service handling.",
        )

    if _low_confidence_escalation(state):
        return (
            "escalate",
            True,
            "Intent confidence was below the approved floor; escalating conservatively.",
        )

    if intent == "policy_faq" or intent == "topup_offer":
        return (
            "allow",
            False,
            "Informational or eligibility lookup may proceed without escalation.",
        )

    if intent == "rejection_reason":
        return (
            "allow",
            False,
            "Customer-safe rejection explanation may proceed.",
        )

    return _informational_allowance(state)


def _assign_step_indexes(
    state: AgentState,
    *,
    prohibited_indexes: tuple[int, ...],
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    approved: list[int] = []
    blocked = list(prohibited_indexes)
    conditional: list[int] = []

    for index, step in enumerate(state.tool_steps):
        if index in prohibited_indexes:
            continue
        if step.planner_condition == PLANNER_CONDITION_AFTER_BUREAU_CLOSURE_LETTER:
            conditional.append(index)
        else:
            approved.append(index)

    return tuple(approved), tuple(blocked), tuple(conditional)


def _collect_allowed_actions_from_steps(
    state: AgentState,
    approved_indexes: tuple[int, ...],
    conditional_indexes: tuple[int, ...],
    *,
    escalation_required: bool,
) -> tuple[str, ...]:
    actions: list[str] = []
    seen: set[str] = set()

    def add(action: str) -> None:
        if action not in seen:
            seen.add(action)
            actions.append(action)

    for index in (*approved_indexes, *conditional_indexes):
        step = state.tool_steps[index]
        for action in TOOL_TO_ALLOWED_ACTIONS.get(step.tool_name, ()):
            add(action)

    if escalation_required:
        add(ACTION_CREATE_HUMAN_REVIEW_TICKET)

    return tuple(actions)


def evaluate_guardrails(
    state: AgentState,
    *,
    integrity: PlanIntegrityResult,
) -> GuardrailEvaluationResult:
    """Return deterministic guardrail authorization for the planned workflow."""
    if integrity.prohibited_step_indexes:
        blocked = tuple(range(len(state.tool_steps)))
        return GuardrailEvaluationResult(
            decision="block",
            reason="Prohibited action or parameter detected in tool plan.",
            escalation_required=True,
            allowed_actions=(),
            approved_step_indexes=(),
            blocked_step_indexes=blocked,
            conditional_step_indexes=(),
            policy_version=GUARDRAIL_POLICY_VERSION,
        )

    decision, escalation_required, reason = _overall_decision(state)
    approved, blocked, conditional = _assign_step_indexes(
        state,
        prohibited_indexes=integrity.prohibited_step_indexes,
    )
    allowed_actions = _collect_allowed_actions_from_steps(
        state,
        approved,
        conditional,
        escalation_required=escalation_required,
    )

    return GuardrailEvaluationResult(
        decision=decision,
        reason=reason[:MAX_GUARDRAIL_REASON_LENGTH],
        escalation_required=escalation_required,
        allowed_actions=allowed_actions,
        approved_step_indexes=approved,
        blocked_step_indexes=blocked,
        conditional_step_indexes=conditional,
        policy_version=GUARDRAIL_POLICY_VERSION,
    )
