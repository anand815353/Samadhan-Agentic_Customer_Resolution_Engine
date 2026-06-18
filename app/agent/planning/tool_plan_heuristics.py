"""Deterministic secondary-tool and conditional-step heuristics (T-057)."""

from __future__ import annotations

from app.agent.planning.tool_plan_types import (
    PLANNER_CONDITION_AFTER_BUREAU_CLOSURE_LETTER,
    ToolPlanStep,
)
from app.tickets.constants import TicketIntent
from app.tools.constants import ToolName

_KYC_KEYWORDS: frozenset[str] = frozenset(
    {
        "kyc",
        "document",
        "upload",
        "reupload",
        "verification",
        "bank statement",
    }
)

_APPLICATION_CONTEXT_KEYWORDS: frozenset[str] = frozenset(
    {
        "reupload",
        "marked for",
        "pending",
        "application status",
        "loan status",
        "still pending",
    }
)

_CLOSED_LOAN_KEYWORDS: frozenset[str] = frozenset(
    {
        "closed my loan",
        "closed loan",
        "paid off",
        "paid-off",
        "closed account",
        "loan is closed",
        "loan was closed",
        "i closed",
    }
)

_BUREAU_MISMATCH_KEYWORDS: frozenset[str] = frozenset(
    {
        "paid off",
        "paid-off",
        "still active",
        "still showing",
        "still show",
        "mismatch",
        "incorrect",
        "wrong status",
        "cibil",
    }
)

_BUREAU_LAG_ONLY_PATTERNS: tuple[str, ...] = (
    "when will",
    "how long",
    "how many days",
    "update after",
    "days until",
    "when does",
    "when do",
)


def _normalize_message(message: str | None) -> str:
    return (message or "").strip().lower()


def _contains_any(text: str, keywords: frozenset[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _contains_lag_only_pattern(text: str) -> bool:
    return any(pattern in text for pattern in _BUREAU_LAG_ONLY_PATTERNS)


def should_append_kyc_document_for_loan_status(message: str | None) -> bool:
    text = _normalize_message(message)
    if not text:
        return False
    if _contains_any(text, _KYC_KEYWORDS):
        return True
    return "application" in text and ("stage" in text or "status" in text or "pending" in text)


def should_append_loan_status_for_kyc(message: str | None) -> bool:
    return _contains_any(_normalize_message(message), _APPLICATION_CONTEXT_KEYWORDS)


def should_append_loan_status_for_closed_loan_context(message: str | None) -> bool:
    return _contains_any(_normalize_message(message), _CLOSED_LOAN_KEYWORDS)


def should_plan_bureau_closure_letter(message: str | None) -> bool:
    text = _normalize_message(message)
    if not text:
        return False
    if _contains_lag_only_pattern(text) and not _contains_any(text, _BUREAU_MISMATCH_KEYWORDS):
        return False
    if _contains_lag_only_pattern(text) and "still" not in text:
        return False
    return _contains_any(text, _BUREAU_MISMATCH_KEYWORDS)


def append_secondary_tools(
    intent: TicketIntent,
    primary_steps: tuple[ToolPlanStep, ...],
    *,
    normalized_message: str | None,
) -> list[ToolPlanStep]:
    """Return primary steps plus deterministic secondary or conditional steps."""
    steps: list[ToolPlanStep] = list(primary_steps)
    existing: set[ToolName] = {step.tool_name for step in steps}

    def append_if_missing(step: ToolPlanStep) -> None:
        if step.tool_name not in existing:
            steps.append(step)
            existing.add(step.tool_name)

    if intent == "loan_application_status" and should_append_kyc_document_for_loan_status(
        normalized_message
    ):
        append_if_missing(ToolPlanStep(tool_name="KYCDocumentTool"))

    if intent == "kyc_document_issue" and should_append_loan_status_for_kyc(normalized_message):
        append_if_missing(ToolPlanStep(tool_name="LoanStatusTool"))

    if intent in {"charges_refund_reversal", "noc_closure_certificate"}:
        if should_append_loan_status_for_closed_loan_context(normalized_message):
            append_if_missing(ToolPlanStep(tool_name="LoanStatusTool"))

    if intent == "bureau_reporting_issue" and should_plan_bureau_closure_letter(
        normalized_message
    ):
        append_if_missing(
            ToolPlanStep(
                tool_name="DocumentGenerationTool",
                document_type="closure_letter",
                planner_condition=PLANNER_CONDITION_AFTER_BUREAU_CLOSURE_LETTER,
            )
        )

    return steps
