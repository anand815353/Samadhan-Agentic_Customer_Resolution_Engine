"""Deterministic response safety validation (T-061)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.agent.response.response_types import (
    FORBIDDEN_INTERNAL_PHRASES,
    FORBIDDEN_REAL_ACTION_PHRASES,
    SUCCESS_CLAIM_PHRASES,
)
from app.agent.response.trusted_facts import TrustedResponseFacts
from app.common.masking import sensitive_violation_kind
from app.tickets.id_generation import TICKET_ID_PATTERN

_TICKET_ID_SEARCH_RE = re.compile(r"TKT-\d{4}-\d{4}")
_SR_ID_SEARCH_RE = re.compile(r"SR-\d{4}-\d{4}")
_POLICY_ID_RE = re.compile(r"POL-[A-Z0-9-]+")
_TRUSTED_TICKET_ID_RE = re.compile(TICKET_ID_PATTERN)


@dataclass(frozen=True)
class ResponseSafetyResult:
    passed: bool
    reason: str | None = None


def _validate_ids(text: str, facts: TrustedResponseFacts) -> ResponseSafetyResult | None:
    for ticket_id in _TICKET_ID_SEARCH_RE.findall(text):
        if not _TRUSTED_TICKET_ID_RE.match(ticket_id) or ticket_id != facts.ticket_id:
            return ResponseSafetyResult(
                passed=False,
                reason="response mentions an untrusted ticket ID",
            )

    trusted_sr_ids = {facts.service_request_id} if facts.service_request_id else set()
    for sr_id in _SR_ID_SEARCH_RE.findall(text):
        if sr_id not in trusted_sr_ids:
            return ResponseSafetyResult(
                passed=False,
                reason="response mentions an untrusted service-request ID",
            )

    if facts.service_request_id and facts.service_request_id not in text:
        if facts.customer_response_type in {"confirm_service_request", "confirm_mock_document"}:
            return ResponseSafetyResult(
                passed=False,
                reason="required service-request ID missing from response",
            )

    trusted_policy_ids = {snippet.document_id for snippet in facts.policy_snippets}
    for policy_id in _POLICY_ID_RE.findall(text):
        if policy_id not in trusted_policy_ids:
            return ResponseSafetyResult(
                passed=False,
                reason="response mentions an untrusted policy source ID",
            )
    return None


def _validate_forbidden_phrases(text: str) -> ResponseSafetyResult | None:
    lowered = text.lower()
    for phrase in FORBIDDEN_INTERNAL_PHRASES:
        if phrase in lowered:
            return ResponseSafetyResult(
                passed=False,
                reason=f"forbidden internal phrase: {phrase}",
            )
    for phrase in FORBIDDEN_REAL_ACTION_PHRASES:
        if phrase in lowered:
            return ResponseSafetyResult(
                passed=False,
                reason=f"forbidden real-action phrase: {phrase}",
            )
    return None


def _validate_pii(text: str) -> ResponseSafetyResult | None:
    violation = sensitive_violation_kind(text)
    if violation is not None:
        return ResponseSafetyResult(
            passed=False,
            reason=f"unmasked sensitive data: {violation}",
        )
    return None


def _validate_fact_consistency(text: str, facts: TrustedResponseFacts) -> ResponseSafetyResult | None:
    lowered = text.lower()
    if not facts.completed_tool_actions and not facts.tool_summaries:
        for phrase in SUCCESS_CLAIM_PHRASES:
            if phrase in lowered:
                return ResponseSafetyResult(
                    passed=False,
                    reason="response claims completion without successful tool outputs",
                )

    if facts.customer_response_type == "explain_no_approved_answer" and not facts.policy_snippets:
        if any(word in lowered for word in ("according to policy", "as per policy", "policy states")):
            return ResponseSafetyResult(
                passed=False,
                reason="response fabricates policy content without approved grounding",
            )

    if any(part.endswith((".pdf", ".json", ".csv")) for part in text.split()):
        return ResponseSafetyResult(
            passed=False,
            reason="response exposes filesystem path",
        )

    if facts.turnaround_time_text is None:
        for phrase in ("24-48", "24–48", "within 24 hours", "within 48 hours"):
            if phrase in lowered:
                return ResponseSafetyResult(
                    passed=False,
                    reason="response invents turnaround time",
                )
    return None


def _validate_escalation_wording(text: str, facts: TrustedResponseFacts) -> ResponseSafetyResult | None:
    if not facts.escalation_required:
        return None
    lowered = text.lower()
    if "human review" not in lowered and "support team" not in lowered and "support agent" not in lowered:
        return ResponseSafetyResult(
            passed=False,
            reason="escalation response missing Human Review wording",
        )
    return None


def validate_response_safety(text: str, facts: TrustedResponseFacts) -> ResponseSafetyResult:
    """Validate a candidate customer response against trusted facts."""
    normalized = text.strip()
    if not normalized:
        return ResponseSafetyResult(passed=False, reason="empty response")

    for check in (_validate_pii, _validate_forbidden_phrases):
        result = check(normalized)
        if result is not None:
            return result

    for check in (_validate_ids, _validate_fact_consistency, _validate_escalation_wording):
        result = check(normalized, facts)
        if result is not None:
            return result

    return ResponseSafetyResult(passed=True)
