"""Canonical demo service request seed rows for T-023 (aligned with tier-1 demo tickets).

Seed data only. Document generation and mock tools are implemented in later tasks.
"""

from __future__ import annotations

from typing import Any

from app.seed.demo_lending import LN_SNEHA
from app.seed.demo_personas import DEMO_SEED_TIMESTAMP
from app.seed.template_spec import SHEET_SPECS_BY_NAME, header_columns

TKT_SNEHA = "TKT-2026-0004"
TKT_FARHAN = "TKT-2026-0009"
TKT_ANITA = "TKT-2026-0010"

SR_SNEHA_NOC = "SR-2026-0001"
SR_FARHAN_RM = "SR-2026-0002"
SR_ANITA_STATEMENT = "SR-2026-0003"

LN_ANITA = "LN-2026-0010"

_SERVICE_REQUESTS: list[dict[str, Any]] = [
    {
        "service_request_id": SR_SNEHA_NOC,
        "ticket_id": TKT_SNEHA,
        "customer_id": "CUST-004",
        "loan_id": LN_SNEHA,
        "request_type": "noc_request",
        "status": "created",
        "customer_safe_summary": "Your NOC request has been registered and is being processed.",
        "created_by": "system",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "service_request_id": SR_FARHAN_RM,
        "ticket_id": TKT_FARHAN,
        "customer_id": "CUST-009",
        "request_type": "rm_callback",
        "status": "in_progress",
        "customer_safe_summary": "Your relationship manager callback request is in progress.",
        "created_by": "system",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
    },
    {
        "service_request_id": SR_ANITA_STATEMENT,
        "ticket_id": TKT_ANITA,
        "customer_id": "CUST-010",
        "loan_id": LN_ANITA,
        "request_type": "loan_statement",
        "status": "completed",
        "customer_safe_summary": "Your loan statement request has been completed.",
        "created_by": "system",
        "created_at": DEMO_SEED_TIMESTAMP,
        "updated_at": DEMO_SEED_TIMESTAMP,
        "completed_at": DEMO_SEED_TIMESTAMP,
    },
]


def demo_service_request_rows() -> list[dict[str, Any]]:
    return list(_SERVICE_REQUESTS)


def _rows_to_values(sheet_name: str, rows: list[dict[str, Any]]) -> list[list[Any]]:
    columns = header_columns(SHEET_SPECS_BY_NAME[sheet_name])
    return [[row.get(column) for column in columns] for row in rows]


def demo_service_request_row_values() -> list[list[Any]]:
    return _rows_to_values("service_requests", demo_service_request_rows())


def service_request_alignment_errors() -> list[str]:
    """Validate service request seed coverage against demo tickets and loans."""
    errors: list[str] = []
    ticket_ids = {row["ticket_id"] for row in _SERVICE_REQUESTS}
    expected_tickets = {TKT_SNEHA, TKT_FARHAN, TKT_ANITA}

    if ticket_ids != expected_tickets:
        errors.append("service request seed must cover all three tier-1 demo tickets")

    sr_ids = [row["service_request_id"] for row in _SERVICE_REQUESTS]
    if len(sr_ids) != len(set(sr_ids)):
        errors.append("duplicate service_request_id in seed")

    sneha = next(row for row in _SERVICE_REQUESTS if row["service_request_id"] == SR_SNEHA_NOC)
    if sneha.get("loan_id") != LN_SNEHA:
        errors.append("Sneha NOC service request must link to LN-2026-0004")

    anita = next(row for row in _SERVICE_REQUESTS if row["service_request_id"] == SR_ANITA_STATEMENT)
    if anita.get("status") != "completed" or not anita.get("completed_at"):
        errors.append("Anita statement SR must be completed with completed_at")

    return errors
