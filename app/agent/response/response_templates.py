"""Deterministic customer response templates (T-061)."""

from __future__ import annotations

from app.agent.response.trusted_facts import TrustedResponseFacts
from app.agent.resolution.resolution_types import CustomerResponseType


def _join_summaries(facts: TrustedResponseFacts) -> str:
    if not facts.tool_summaries:
        return ""
    return " ".join(facts.tool_summaries)


def _mock_disclaimer(facts: TrustedResponseFacts) -> str:
    if not facts.mock_disclaimer_required:
        return ""
    return (
        " This is a mock demo workflow only; no real bank, bureau, refund, freeze, "
        "or disbursement action was performed."
    )


def _ticket_line(facts: TrustedResponseFacts) -> str:
    return f"Ticket ID: {facts.ticket_id}."


def _sr_line(facts: TrustedResponseFacts) -> str:
    if facts.service_request_id:
        return f" Service request ID: {facts.service_request_id}."
    return ""


def _document_line(facts: TrustedResponseFacts) -> str:
    if not facts.document_labels:
        return ""
    labels = ", ".join(facts.document_labels)
    return f" A mock {labels} is available in the demo documents section."


def render_deterministic_response(facts: TrustedResponseFacts) -> str:
    """Render a safe deterministic response from trusted facts."""
    response_type: CustomerResponseType = facts.customer_response_type  # type: ignore[assignment]
    summaries = _join_summaries(facts)
    disclaimer = _mock_disclaimer(facts)

    if response_type == "request_more_information":
        return (
            "Thank you for your message. I need a little more information to help you safely. "
            "Please share the specific loan or issue you are asking about. "
            f"{_ticket_line(facts)}"
        )

    if response_type == "explain_no_approved_answer":
        return (
            "Thank you for your question. I could not confirm an approved policy answer "
            "from the available sources. "
            f"{_ticket_line(facts)} "
            "Our support team can review this further if needed."
        )

    if response_type == "explain_safe_failure":
        return (
            "Thank you for contacting us. I was not able to complete the requested check "
            "safely in this demo workflow. "
            f"{_ticket_line(facts)} "
            "Please contact support if you need further help."
        )

    if response_type == "explain_policy":
        if facts.policy_snippets:
            snippet = facts.policy_snippets[0]
            return (
                f"Thank you for your question. Based on {snippet.title} "
                f"({snippet.document_id}): {snippet.snippet_text} "
                f"{_ticket_line(facts)}"
            )
        return (
            "Thank you for your policy question. I could not confirm an approved answer "
            "from the available policy sources. "
            f"{_ticket_line(facts)}"
        )

    if response_type == "confirm_service_request":
        return (
            "Thank you for your request. Your service request has been created in the demo workflow. "
            f"{summaries} "
            f"{_ticket_line(facts)}{_sr_line(facts)}"
            f"{disclaimer}"
        )

    if response_type == "confirm_mock_document":
        return (
            "Thank you for your request. "
            f"{summaries}"
            f"{_document_line(facts)}"
            f"{_ticket_line(facts)}{_sr_line(facts)}"
            f"{disclaimer}"
        )

    if response_type == "explain_offer_eligibility":
        lead_text = summaries or "The demo eligibility check has been completed."
        return (
            f"Thank you for asking about a top-up offer. {lead_text} "
            "This demo does not approve or disburse funds. "
            f"{_ticket_line(facts)}{_sr_line(facts)}"
        )

    if response_type == "explain_and_escalate":
        checked = summaries or "Your request has been reviewed in the demo workflow."
        if facts.intent == "fraud_security_issue":
            return (
                "Thank you for reporting this urgently. This requires critical Human Review. "
                f"{checked} "
                f"{_ticket_line(facts)} "
                "A simulated protective action may be recorded in the demo only; "
                "no real account or card freeze was performed."
                f"{disclaimer}"
            )
        return (
            "Thank you for your message. I reviewed the available records and this case "
            "requires Human Review. "
            f"{checked} "
            f"{_ticket_line(facts)}{_sr_line(facts)} "
            "Our support team will review your request."
            f"{disclaimer}"
        )

    checked = summaries or "I reviewed the available information in the demo workflow."
    return (
        f"Thank you for contacting us. {checked} "
        f"{_ticket_line(facts)}{_sr_line(facts)}"
        f"{disclaimer}"
    ).strip()
