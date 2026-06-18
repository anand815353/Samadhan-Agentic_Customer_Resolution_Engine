"""Guards against persisting workflow updates onto stale ticket rows."""

from __future__ import annotations

from app.agent.exceptions import TicketUpdateValidationError
from app.tickets.constants import TERMINAL_STATUSES, TicketStatus
from app.tickets.models import TicketDocument

_ADVANCED_HR_STATUSES: frozenset[TicketStatus] = frozenset(
    {
        "under_review",
        "need_customer_input",
        "resolved_by_agent",
        "escalated_further",
    }
)


def assert_ticket_mutable_for_workflow(
    ticket: TicketDocument,
    *,
    planned_status: TicketStatus,
    ticket_id: str,
) -> None:
    """Reject updates when the ticket row is terminal or advanced HR state blocks replay."""
    if ticket.status in TERMINAL_STATUSES:
        raise TicketUpdateValidationError(
            f"ticket {ticket_id} is terminal ({ticket.status}); workflow update rejected",
        )
    if ticket.status in _ADVANCED_HR_STATUSES and planned_status == "escalated_to_human":
        raise TicketUpdateValidationError(
            f"ticket {ticket_id} is already in advanced human review ({ticket.status})",
        )
