"""Canonical demo ticket seed rows for T-021 (aligned with personas and TICKETING_AND_RISK_MODEL).

Seed data only. Chat routing and LangGraph integration are implemented in later tasks.
"""

from __future__ import annotations

from typing import Any

from app.seed.demo_personas import DEMO_CUSTOMERS, DEMO_SEED_TIMESTAMP
from app.seed.template_spec import SHEET_SPECS_BY_NAME, header_columns

# Stable ticket IDs — one per demo persona (TKT-2026-0006 satisfies fraud_cases FK from T-018).
TKT_RAMESH = "TKT-2026-0001"
TKT_PRIYA = "TKT-2026-0002"
TKT_ARJUN = "TKT-2026-0003"
TKT_SNEHA = "TKT-2026-0004"
TKT_IMRAN = "TKT-2026-0005"
TKT_KAVITA = "TKT-2026-0006"
TKT_MOHIT = "TKT-2026-0007"
TKT_NEHA = "TKT-2026-0008"
TKT_FARHAN = "TKT-2026-0009"
TKT_ANITA = "TKT-2026-0010"

CUSTOMER_IDS = {customer.customer_id for customer in DEMO_CUSTOMERS}

_TICKETS: list[dict[str, Any]] = [
    {
        "ticket_id": TKT_RAMESH,
        "customer_id": "CUST-001",
        "user_id": "USR-CUST-001",
        "session_id": "SES-2026-0001",
        "ticket_class": "tier_2_conversation",
        "intent": "loan_application_status",
        "risk_level": "medium",
        "priority": "medium",
        "status": "auto_resolved",
        "subject": "Loan pending due to KYC",
        "description": "Customer asked why loan application is still pending.",
        "source_channel": "web_chat",
        "last_customer_message": "My loan is still pending. What is the issue?",
        "last_ai_response": "Your application is pending KYC document verification.",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "ticket_id": TKT_PRIYA,
        "customer_id": "CUST-002",
        "user_id": "USR-CUST-002",
        "session_id": "SES-2026-0002",
        "ticket_class": "tier_2_conversation",
        "intent": "rejection_reason",
        "risk_level": "medium",
        "priority": "medium",
        "status": "auto_closed",
        "subject": "Loan rejection explanation",
        "description": "Customer requested rejection reason for declined application.",
        "source_channel": "web_chat",
        "last_customer_message": "Why was my loan rejected?",
        "last_ai_response": "Your application did not meet current eligibility criteria.",
        "closure_reason": "Customer received safe rejection explanation.",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
        "closed_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "ticket_id": TKT_ARJUN,
        "customer_id": "CUST-003",
        "user_id": "USR-CUST-003",
        "session_id": "SES-2026-0003",
        "ticket_class": "human_review",
        "intent": "emi_payment_issue",
        "risk_level": "high",
        "priority": "high",
        "status": "escalated_to_human",
        "subject": "Duplicate EMI debit",
        "description": "Customer reported EMI was deducted twice for the same cycle.",
        "source_channel": "web_chat",
        "escalation_reason": "Financial dispute — duplicate EMI debit requires human review.",
        "last_customer_message": "My EMI was deducted twice this month.",
        "last_ai_response": "Your case has been escalated for human review.",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "ticket_id": TKT_SNEHA,
        "customer_id": "CUST-004",
        "user_id": "USR-CUST-004",
        "session_id": "SES-2026-0004",
        "ticket_class": "tier_1_service_request",
        "intent": "noc_closure_certificate",
        "risk_level": "medium",
        "priority": "medium",
        "status": "service_requested",
        "subject": "NOC pending after loan closure",
        "description": "Customer closed loan and is waiting for NOC document.",
        "source_channel": "web_chat",
        "service_request_id": "SR-2026-0001",
        "last_customer_message": "I closed my loan. Where is my NOC?",
        "last_ai_response": "We will create a service request for your NOC.",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "ticket_id": TKT_IMRAN,
        "customer_id": "CUST-005",
        "user_id": "USR-CUST-005",
        "session_id": "SES-2026-0005",
        "ticket_class": "human_review",
        "intent": "bureau_reporting_issue",
        "risk_level": "high",
        "priority": "high",
        "status": "under_review",
        "subject": "CIBIL still shows active loan",
        "description": "Customer reports bureau still shows closed loan as active.",
        "source_channel": "web_chat",
        "assigned_agent_id": "USR-AGENT-001",
        "escalation_reason": "Bureau/CIBIL mismatch requires human review.",
        "last_customer_message": "CIBIL still shows my loan as active after closure.",
        "last_ai_response": "A support agent is reviewing your bureau reporting case.",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "ticket_id": TKT_KAVITA,
        "customer_id": "CUST-006",
        "user_id": "USR-CUST-006",
        "session_id": "SES-2026-0006",
        "ticket_class": "human_review",
        "intent": "fraud_security_issue",
        "risk_level": "critical",
        "priority": "critical",
        "status": "escalated_to_human",
        "subject": "Unauthorized transaction SMS alert",
        "description": "Customer received SMS for a transaction they did not make.",
        "source_channel": "web_chat",
        "escalation_reason": "Fraud/security alert — mandatory human review.",
        "last_customer_message": "I got an SMS for a transaction I did not make.",
        "last_ai_response": "Your security concern has been escalated immediately.",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "ticket_id": TKT_MOHIT,
        "customer_id": "CUST-007",
        "user_id": "USR-CUST-007",
        "session_id": "SES-2026-0007",
        "ticket_class": "tier_2_conversation",
        "intent": "topup_offer",
        "risk_level": "medium",
        "priority": "medium",
        "status": "auto_resolved",
        "subject": "Top-up eligibility inquiry",
        "description": "Customer asked about pre-approved top-up offer eligibility.",
        "source_channel": "web_chat",
        "last_customer_message": "Am I eligible for a top-up loan?",
        "last_ai_response": "You have a pre-approved top-up offer available.",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "ticket_id": TKT_NEHA,
        "customer_id": "CUST-008",
        "user_id": "USR-CUST-008",
        "session_id": "SES-2026-0008",
        "ticket_class": "tier_2_conversation",
        "intent": "topup_offer",
        "risk_level": "medium",
        "priority": "medium",
        "status": "auto_closed",
        "subject": "Top-up not eligible",
        "description": "Customer asked about top-up but is not eligible.",
        "source_channel": "web_chat",
        "last_customer_message": "Can I get a top-up on my loan?",
        "last_ai_response": "No pre-approved top-up offer is available at this time.",
        "closure_reason": "Customer received eligibility explanation.",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
        "closed_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "ticket_id": TKT_FARHAN,
        "customer_id": "CUST-009",
        "user_id": "USR-CUST-009",
        "session_id": "SES-2026-0009",
        "ticket_class": "tier_1_service_request",
        "intent": "rm_redirection",
        "risk_level": "medium",
        "priority": "medium",
        "status": "in_progress",
        "subject": "RM callback request",
        "description": "Customer wants to speak with relationship manager.",
        "source_channel": "web_chat",
        "service_request_id": "SR-2026-0002",
        "last_customer_message": "I want to speak to my RM.",
        "last_ai_response": "We will register a callback request for your RM.",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "ticket_id": TKT_ANITA,
        "customer_id": "CUST-010",
        "user_id": "USR-CUST-010",
        "session_id": "SES-2026-0010",
        "ticket_class": "tier_1_service_request",
        "intent": "loan_statement_request",
        "risk_level": "medium",
        "priority": "medium",
        "status": "service_completed",
        "subject": "Loan statement for tax filing",
        "description": "Customer needs loan statement document.",
        "source_channel": "web_chat",
        "service_request_id": "SR-2026-0003",
        "last_customer_message": "Please generate my loan statement for tax filing.",
        "last_ai_response": "We will create a loan statement service request.",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
]


def demo_ticket_rows() -> list[dict[str, Any]]:
    return list(_TICKETS)


def _rows_to_values(sheet_name: str, rows: list[dict[str, Any]]) -> list[list[Any]]:
    columns = header_columns(SHEET_SPECS_BY_NAME[sheet_name])
    return [[row.get(column) for column in columns] for row in rows]


def demo_ticket_row_values() -> list[list[Any]]:
    return _rows_to_values("tickets", demo_ticket_rows())


def ticket_alignment_errors() -> list[str]:
    """Validate ticket seed coverage against demo personas."""
    errors: list[str] = []
    rows_by_customer = {row["customer_id"]: row for row in _TICKETS}

    for customer in DEMO_CUSTOMERS:
        if customer.customer_id not in rows_by_customer:
            errors.append(f"missing ticket for {customer.customer_id}")

    kavita = rows_by_customer.get("CUST-006")
    if kavita is None or kavita["ticket_id"] != TKT_KAVITA:
        errors.append("CUST-006 must have TKT-2026-0006 fraud ticket")
    if kavita and kavita.get("risk_level") != "critical":
        errors.append("fraud ticket must be critical risk")

    for row in _TICKETS:
        if row["customer_id"] not in CUSTOMER_IDS:
            errors.append(f"unknown customer_id in ticket seed: {row['customer_id']}")

    return errors
