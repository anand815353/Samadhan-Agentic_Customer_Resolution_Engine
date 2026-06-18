"""Deterministic intent-to-tool planning policy (T-057)."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.planning.tool_input_builder import build_tool_input
from app.agent.planning.tool_plan_heuristics import append_secondary_tools
from app.agent.planning.tool_plan_types import (
    MAX_TOOL_PLAN_REASON_LENGTH,
    TOOL_PLANNER_POLICY_VERSION,
    ToolPlanStep,
)
from app.agent.state import AgentState
from app.tickets.constants import ALL_TICKET_INTENTS, TicketIntent
from app.tools.constants import ALL_TOOL_NAMES

_PRIMARY_TOOL_STEPS: dict[TicketIntent, tuple[ToolPlanStep, ...]] = {
    "loan_application_status": (ToolPlanStep(tool_name="LoanStatusTool"),),
    "rejection_reason": (ToolPlanStep(tool_name="RejectionReasonTool"),),
    "kyc_document_issue": (ToolPlanStep(tool_name="KYCDocumentTool"),),
    "emi_payment_issue": (
        ToolPlanStep(tool_name="RepaymentTool"),
        ToolPlanStep(tool_name="TransactionTool"),
    ),
    "charges_refund_reversal": (ToolPlanStep(tool_name="TransactionTool"),),
    "policy_faq": (ToolPlanStep(tool_name="PolicyRAGTool"),),
    "rm_redirection": (ToolPlanStep(tool_name="RMRedirectTool"),),
    "loan_statement_request": (
        ToolPlanStep(
            tool_name="DocumentGenerationTool",
            document_type="loan_statement",
        ),
    ),
    "noc_closure_certificate": (
        ToolPlanStep(
            tool_name="DocumentGenerationTool",
            document_type="noc",
        ),
    ),
    "bureau_reporting_issue": (ToolPlanStep(tool_name="BureauReportingTool"),),
    "fraud_security_issue": (
        ToolPlanStep(tool_name="FraudSecurityTool"),
        ToolPlanStep(tool_name="TransactionTool"),
    ),
    "topup_offer": (ToolPlanStep(tool_name="OfferEligibilityTool"),),
    "unknown": (),
}

_PLAN_REASON_BY_INTENT: dict[TicketIntent, str] = {
    "loan_application_status": "Loan status lookup planned for application-status intent.",
    "rejection_reason": "Customer-safe rejection lookup planned.",
    "kyc_document_issue": "KYC document guidance tool planned.",
    "emi_payment_issue": "Repayment and transaction review tools planned in order.",
    "charges_refund_reversal": "Transaction review tool planned for charge dispute.",
    "policy_faq": "Policy knowledge tool planned for FAQ intent.",
    "rm_redirection": "RM callback tool planned.",
    "loan_statement_request": "Loan statement document generation planned.",
    "noc_closure_certificate": "NOC or closure certificate generation planned.",
    "bureau_reporting_issue": "Bureau reporting review planned with optional closure letter.",
    "fraud_security_issue": "Fraud security and transaction review tools planned in order.",
    "topup_offer": "Top-up eligibility lookup planned.",
    "unknown": (
        "Unknown intent requires conservative handling; no automated tool was selected."
    ),
}


@dataclass(frozen=True)
class ToolPlanResult:
    """Outcome of deterministic tool planning."""

    steps: tuple[ToolPlanStep, ...]
    reason: str
    policy_version: str = TOOL_PLANNER_POLICY_VERSION
    retrieval_context_noted: bool = False


def supported_tool_plan_intents() -> tuple[TicketIntent, ...]:
    return ALL_TICKET_INTENTS


def _validate_planned_tool_names(steps: list[ToolPlanStep]) -> None:
    allowed = set(ALL_TOOL_NAMES)
    for step in steps:
        if step.tool_name not in allowed:
            raise ValueError(f"unregistered tool planned: {step.tool_name}")


def _build_reason(
    intent: TicketIntent,
    *,
    steps: list[ToolPlanStep],
    retrieval_context_noted: bool,
) -> str:
    base = _PLAN_REASON_BY_INTENT[intent]
    if not steps:
        return base[:MAX_TOOL_PLAN_REASON_LENGTH]

    tool_names = ", ".join(step.tool_name for step in steps)
    reason = f"{base} Planned tools: {tool_names}."
    if retrieval_context_noted and intent == "policy_faq":
        reason = (
            f"{reason} Workflow retrieval already gathered policy context for grounding."
        )
    return reason[:MAX_TOOL_PLAN_REASON_LENGTH]


def plan_tools(state: AgentState) -> ToolPlanResult:
    """Return an ordered tool plan for the classified intent (plan only; no execution)."""
    if state.intent_classification is None:
        raise ValueError("intent classification is required before tool planning")

    intent = state.intent_classification.intent
    if intent not in ALL_TICKET_INTENTS:
        raise ValueError("unsupported intent for tool planning")

    primary = _PRIMARY_TOOL_STEPS[intent]
    if intent == "unknown":
        return ToolPlanResult(steps=(), reason=_PLAN_REASON_BY_INTENT["unknown"])

    expanded = append_secondary_tools(
        intent,
        primary,
        normalized_message=state.normalized_message or state.customer_message,
    )
    _validate_planned_tool_names(expanded)

    for step in expanded:
        build_tool_input(step, intent=intent, state=state)

    retrieval_context_noted = bool(
        state.retrieval is not None
        and state.retrieval.retrieval_required
        and state.retrieval.result is not None
        and not state.retrieval.result.unavailable
        and state.retrieval.result.chunks
    )

    reason = _build_reason(
        intent,
        steps=expanded,
        retrieval_context_noted=retrieval_context_noted,
    )
    return ToolPlanResult(
        steps=tuple(expanded),
        reason=reason,
        retrieval_context_noted=retrieval_context_noted,
    )
