"""Ticket class promotion rules for workflow persistence."""

from __future__ import annotations

from app.tickets.constants import (
    TICKET_CLASS_HUMAN_REVIEW,
    TICKET_CLASS_TIER_1,
    TICKET_CLASS_TIER_2,
    TicketClass,
)

_CLASS_RANK: dict[TicketClass, int] = {
  TICKET_CLASS_TIER_2: 0,
  TICKET_CLASS_TIER_1: 1,
  TICKET_CLASS_HUMAN_REVIEW: 2,
}


def merge_ticket_class(current: TicketClass, desired: TicketClass) -> TicketClass:
    """Return the higher-ranked ticket class (never downgrade)."""
    if _CLASS_RANK[desired] > _CLASS_RANK[current]:
        return desired
    return current
