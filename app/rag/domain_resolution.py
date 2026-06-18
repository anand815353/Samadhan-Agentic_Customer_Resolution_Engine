"""Deterministic policy domain resolution for retrieval (shared by tool and agent nodes)."""

from __future__ import annotations

from typing import Any

from app.rag.constants import ALL_POLICY_DOMAINS, INTENT_TO_POLICY_DOMAIN
from app.tickets.constants import TicketIntent


def infer_domain_from_query(query: str) -> str | None:
    """Infer a policy domain from normalized customer text (policy_faq support)."""
    text = query.lower()
    if any(token in text for token in ("prepay", "prepayment", "foreclosure", "part payment")):
        return "loan_status"
    if "kyc" in text or "document" in text:
        return "kyc"
    if "top-up" in text or "topup" in text or "top up" in text:
        return "topup"
    if "emi" in text or "duplicate debit" in text:
        return "emi"
    if "refund" in text or "reversal" in text:
        return "refund"
    if "noc" in text or "closure" in text or "statement" in text:
        return "noc"
    if "bureau" in text or "cibil" in text:
        return "bureau"
    if "fraud" in text or "security" in text:
        return "fraud"
    if "relationship manager" in text or "callback" in text or " rm " in f" {text} ":
        return "rm"
    return None


def resolve_policy_domain(
    intent: TicketIntent,
    query: str,
    *,
    parameters: dict[str, Any] | None = None,
) -> str | None:
    """Map intent and query to a supported policy domain, if determinable."""
    if parameters:
        explicit = parameters.get("domain")
        if isinstance(explicit, str) and explicit.strip():
            domain = explicit.strip()
            if domain in ALL_POLICY_DOMAINS:
                return domain

    mapped = INTENT_TO_POLICY_DOMAIN.get(intent)
    if mapped is not None:
        return mapped

    if intent == "policy_faq":
        return infer_domain_from_query(query)

    return None
