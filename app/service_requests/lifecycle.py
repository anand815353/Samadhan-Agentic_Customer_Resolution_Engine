"""Service request lifecycle transition rules."""

from __future__ import annotations

from app.service_requests.constants import (
    TERMINAL_SR_STATUSES,
    ServiceRequestActor,
    ServiceRequestStatus,
)
from app.service_requests.exceptions import InvalidServiceRequestTransitionError

_SR_TRANSITIONS: dict[tuple[str, str], frozenset[str] | None] = {
    ("created", "in_progress"): frozenset({"system", "agent", "admin"}),
    ("created", "cancelled"): frozenset({"customer", "agent", "admin"}),
    ("in_progress", "completed"): frozenset({"system", "agent"}),
    ("in_progress", "failed"): frozenset({"system"}),
    ("in_progress", "cancelled"): frozenset({"admin"}),
}

# SR status → ticket status when sync_ticket=True
SR_TO_TICKET_STATUS: dict[str, str] = {
    "created": "service_requested",
    "in_progress": "in_progress",
    "completed": "service_completed",
    "failed": "failed",
}


def can_transition(
    *,
    from_status: ServiceRequestStatus,
    to_status: ServiceRequestStatus,
    actor: ServiceRequestActor,
) -> bool:
    try:
        validate_transition(from_status=from_status, to_status=to_status, actor=actor)
        return True
    except InvalidServiceRequestTransitionError:
        return False


def validate_transition(
    *,
    from_status: ServiceRequestStatus,
    to_status: ServiceRequestStatus,
    actor: ServiceRequestActor,
) -> None:
    """Raise InvalidServiceRequestTransitionError when transition is not allowed."""
    if from_status in TERMINAL_SR_STATUSES:
        raise InvalidServiceRequestTransitionError(
            f"cannot transition from terminal status '{from_status}'",
            from_status=from_status,
            to_status=to_status,
        )

    key = (from_status, to_status)
    if key not in _SR_TRANSITIONS:
        raise InvalidServiceRequestTransitionError(
            f"transition '{from_status}' → '{to_status}' not allowed",
            from_status=from_status,
            to_status=to_status,
        )

    allowed_actors = _SR_TRANSITIONS[key]
    if allowed_actors is not None and actor not in allowed_actors:
        raise InvalidServiceRequestTransitionError(
            f"actor '{actor}' cannot perform '{from_status}' → '{to_status}'",
            from_status=from_status,
            to_status=to_status,
        )


def ticket_status_for_sr_transition(to_status: ServiceRequestStatus) -> str | None:
    """Return paired ticket status for SR transition, or None if no sync."""
    return SR_TO_TICKET_STATUS.get(to_status)
