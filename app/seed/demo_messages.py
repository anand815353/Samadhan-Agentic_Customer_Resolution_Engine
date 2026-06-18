"""Canonical demo message seed rows for T-022 (aligned with demo_tickets).

Two messages per ticket: customer query + AI response. Seed data only.
"""

from __future__ import annotations

import json
from typing import Any

from app.messages.constants import META_SOURCE
from app.seed.demo_personas import DEMO_SEED_TIMESTAMP
from app.seed.demo_tickets import demo_ticket_rows
from app.seed.template_spec import SHEET_SPECS_BY_NAME, header_columns

SEED_METADATA = json.dumps({META_SOURCE: "seed"})


def _build_messages() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sequence = 1
    for ticket in demo_ticket_rows():
        customer_msg_id = f"MSG-2026-{sequence:04d}"
        sequence += 1
        ai_msg_id = f"MSG-2026-{sequence:04d}"
        sequence += 1

        rows.append(
            {
                "message_id": customer_msg_id,
                "ticket_id": ticket["ticket_id"],
                "session_id": ticket["session_id"],
                "customer_id": ticket["customer_id"],
                "sender_type": "customer",
                "sender_id": ticket["user_id"],
                "message_text": ticket["last_customer_message"],
                "message_metadata": SEED_METADATA,
                "created_at": DEMO_SEED_TIMESTAMP,
            }
        )
        rows.append(
            {
                "message_id": ai_msg_id,
                "ticket_id": ticket["ticket_id"],
                "session_id": ticket["session_id"],
                "customer_id": ticket["customer_id"],
                "sender_type": "ai",
                "message_text": ticket["last_ai_response"],
                "message_metadata": SEED_METADATA,
                "created_at": DEMO_SEED_TIMESTAMP,
            }
        )
    return rows


_MESSAGES: list[dict[str, Any]] = _build_messages()


def demo_message_rows() -> list[dict[str, Any]]:
    return list(_MESSAGES)


def _rows_to_values(sheet_name: str, rows: list[dict[str, Any]]) -> list[list[Any]]:
    columns = header_columns(SHEET_SPECS_BY_NAME[sheet_name])
    return [[row.get(column) for column in columns] for row in rows]


def demo_message_row_values() -> list[list[Any]]:
    return _rows_to_values("messages", demo_message_rows())


def message_alignment_errors() -> list[str]:
    """Validate message seed coverage against demo tickets."""
    errors: list[str] = []
    tickets = demo_ticket_rows()
    messages = demo_message_rows()

    if len(messages) != len(tickets) * 2:
        errors.append("expected two messages per demo ticket")

    ticket_ids = {ticket["ticket_id"] for ticket in tickets}
    for row in messages:
        if row["ticket_id"] not in ticket_ids:
            errors.append(f"unknown ticket_id in message seed: {row['ticket_id']}")

    message_ids = [row["message_id"] for row in messages]
    if len(message_ids) != len(set(message_ids)):
        errors.append("duplicate message_id in seed")

    return errors
