"""Ticket lifecycle transition rules per ticket class."""

from __future__ import annotations

from dataclasses import dataclass

from app.tickets.constants import (
    TERMINAL_STATUSES,
    TICKET_CLASS_HUMAN_REVIEW,
    TICKET_CLASS_TIER_1,
    TICKET_CLASS_TIER_2,
    TicketClass,
    TicketStatus,
    TransitionActor,
)
from app.tickets.exceptions import InvalidTicketTransitionError

# Tier 2 allowed transitions: (from_status, to_status) -> allowed actors (None = any)
_TIER_2_TRANSITIONS: dict[tuple[str, str], frozenset[str] | None] = {
    ("open", "auto_resolved"): frozenset({"system"}),
    ("open", "need_more_info"): frozenset({"system"}),
    ("open", "auto_closed"): frozenset({"system"}),
    ("auto_resolved", "auto_closed"): frozenset({"system"}),
    ("need_more_info", "open"): frozenset({"system", "customer"}),
    ("need_more_info", "auto_closed"): frozenset({"system"}),
}

# Tier 1 allowed transitions
_TIER_1_TRANSITIONS: dict[tuple[str, str], frozenset[str] | None] = {
    ("open", "service_requested"): frozenset({"system"}),
    ("open", "closed"): frozenset({"support_agent", "admin"}),
    ("service_requested", "in_progress"): frozenset({"system"}),
    ("in_progress", "service_completed"): frozenset({"system"}),
    ("in_progress", "failed"): frozenset({"system"}),
    ("service_completed", "closed"): frozenset({"system", "support_agent", "admin"}),
    ("failed", "escalated_to_human"): frozenset({"system"}),
}

# Human review allowed transitions
_HUMAN_REVIEW_TRANSITIONS: dict[tuple[str, str], frozenset[str] | None] = {
    ("open", "escalated_to_human"): frozenset({"system", "admin"}),
    ("escalated_to_human", "under_review"): frozenset({"support_agent", "admin"}),
    ("escalated_to_human", "need_customer_input"): frozenset({"support_agent", "admin"}),
    ("under_review", "need_customer_input"): frozenset({"support_agent", "admin"}),
    ("need_customer_input", "under_review"): frozenset({"support_agent", "customer", "system"}),
    ("under_review", "resolved_by_agent"): frozenset({"support_agent", "admin"}),
    ("under_review", "escalated_further"): frozenset({"support_agent", "admin"}),
    ("resolved_by_agent", "closed"): frozenset({"support_agent", "admin"}),
    ("escalated_further", "closed"): frozenset({"support_agent", "admin"}),
}

_TRANSITIONS_BY_CLASS: dict[TicketClass, dict[tuple[str, str], frozenset[str] | None]] = {
    TICKET_CLASS_TIER_2: _TIER_2_TRANSITIONS,
    TICKET_CLASS_TIER_1: _TIER_1_TRANSITIONS,
    TICKET_CLASS_HUMAN_REVIEW: _HUMAN_REVIEW_TRANSITIONS,
}

# Statuses that require class mutation when reached from tier_1
_TIER_1_CLASS_MUTATION_TARGETS: frozenset[str] = frozenset({"escalated_to_human"})

# Blocked auto-close statuses for human review
_HUMAN_REVIEW_BLOCKED_STATUSES: frozenset[str] = frozenset({"auto_resolved", "auto_closed"})

# Tier 2 cannot reach these without class mutation
_TIER_2_BLOCKED_STATUSES: frozenset[str] = frozenset(
    {
        "under_review",
        "resolved_by_agent",
        "escalated_further",
        "service_requested",
        "in_progress",
        "service_completed",
        "failed",
        "escalated_to_human",
    }
)

# Tier 1 cannot auto-close
_TIER_1_BLOCKED_STATUSES: frozenset[str] = frozenset({"auto_resolved", "auto_closed"})


@dataclass(frozen=True)
class TransitionResult:
    """Outcome of applying a lifecycle transition."""

    new_status: TicketStatus
    new_ticket_class: TicketClass
    class_mutated: bool


def default_status_for_class(ticket_class: TicketClass) -> TicketStatus:
    if ticket_class == TICKET_CLASS_HUMAN_REVIEW:
        return "escalated_to_human"
    return "open"


def can_transition(
    *,
    ticket_class: TicketClass,
    from_status: TicketStatus,
    to_status: TicketStatus,
    actor: TransitionActor,
    admin_override: bool = False,
) -> bool:
    try:
        validate_transition(
            ticket_class=ticket_class,
            from_status=from_status,
            to_status=to_status,
            actor=actor,
            admin_override=admin_override,
        )
        return True
    except InvalidTicketTransitionError:
        return False


def validate_transition(
    *,
    ticket_class: TicketClass,
    from_status: TicketStatus,
    to_status: TicketStatus,
    actor: TransitionActor,
    admin_override: bool = False,
) -> None:
    """Raise InvalidTicketTransitionError when transition is not allowed."""
    if from_status in TERMINAL_STATUSES:
        if admin_override and from_status == "closed" and to_status == "open" and actor == "admin":
            return
        raise InvalidTicketTransitionError(
            f"cannot transition from terminal status '{from_status}'",
            from_status=from_status,
            to_status=to_status,
        )

    if ticket_class == TICKET_CLASS_HUMAN_REVIEW and to_status in _HUMAN_REVIEW_BLOCKED_STATUSES:
        raise InvalidTicketTransitionError(
            "human_review tickets cannot be auto-closed or auto-resolved",
            from_status=from_status,
            to_status=to_status,
        )

    if ticket_class == TICKET_CLASS_TIER_2 and to_status in _TIER_2_BLOCKED_STATUSES:
        raise InvalidTicketTransitionError(
            f"tier_2 tickets cannot transition to '{to_status}' without class mutation",
            from_status=from_status,
            to_status=to_status,
        )

    if ticket_class == TICKET_CLASS_TIER_1 and to_status in _TIER_1_BLOCKED_STATUSES:
        raise InvalidTicketTransitionError(
            f"tier_1 tickets cannot transition to '{to_status}'",
            from_status=from_status,
            to_status=to_status,
        )

    if ticket_class == TICKET_CLASS_HUMAN_REVIEW and to_status == "closed":
        if actor == "system":
            raise InvalidTicketTransitionError(
                "human_review tickets cannot be closed by system",
                from_status=from_status,
                to_status=to_status,
            )
        if not admin_override:
            allowed_from = frozenset({"resolved_by_agent", "escalated_further"})
            if from_status not in allowed_from:
                raise InvalidTicketTransitionError(
                    f"human_review tickets can only close from {sorted(allowed_from)}",
                    from_status=from_status,
                    to_status=to_status,
                )
            if from_status == "resolved_by_agent" and actor not in ("support_agent", "admin"):
                raise InvalidTicketTransitionError(
                    "resolved_by_agent → closed requires support_agent or admin",
                    from_status=from_status,
                    to_status=to_status,
                )

    effective_class = ticket_class
    if (
        ticket_class == TICKET_CLASS_TIER_1
        and to_status in _TIER_1_CLASS_MUTATION_TARGETS
    ):
        effective_class = TICKET_CLASS_HUMAN_REVIEW

    # Tier 1 paths (including class-mutating escalations) use tier_1 transition table first.
    if ticket_class == TICKET_CLASS_TIER_1:
        tier_1_key = (from_status, to_status)
        if tier_1_key in _TIER_1_TRANSITIONS:
            allowed_actors = _TIER_1_TRANSITIONS[tier_1_key]
            if allowed_actors is not None and actor not in allowed_actors:
                if admin_override and actor == "admin":
                    return
                raise InvalidTicketTransitionError(
                    f"actor '{actor}' cannot perform '{from_status}' → '{to_status}'",
                    from_status=from_status,
                    to_status=to_status,
                )
            return

    transitions = _TRANSITIONS_BY_CLASS.get(effective_class, {})
    key = (from_status, to_status)

    if key not in transitions:
        if admin_override and actor == "admin":
            return
        raise InvalidTicketTransitionError(
            f"transition '{from_status}' → '{to_status}' not allowed for {ticket_class}",
            from_status=from_status,
            to_status=to_status,
        )

    allowed_actors = transitions[key]
    if allowed_actors is not None and actor not in allowed_actors:
        if admin_override and actor == "admin":
            return
        raise InvalidTicketTransitionError(
            f"actor '{actor}' cannot perform '{from_status}' → '{to_status}'",
            from_status=from_status,
            to_status=to_status,
        )


def apply_transition(
    *,
    ticket_class: TicketClass,
    from_status: TicketStatus,
    to_status: TicketStatus,
    actor: TransitionActor,
    admin_override: bool = False,
) -> TransitionResult:
    """Validate and return the post-transition class/status."""
    validate_transition(
        ticket_class=ticket_class,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        admin_override=admin_override,
    )

    new_class = ticket_class
    class_mutated = False
    if (
        ticket_class == TICKET_CLASS_TIER_1
        and to_status in _TIER_1_CLASS_MUTATION_TARGETS
    ):
        new_class = TICKET_CLASS_HUMAN_REVIEW
        class_mutated = True

    if admin_override and from_status == "closed" and to_status == "open" and actor == "admin":
        return TransitionResult(
            new_status=to_status,
            new_ticket_class=ticket_class,
            class_mutated=False,
        )

    return TransitionResult(
        new_status=to_status,
        new_ticket_class=new_class,
        class_mutated=class_mutated,
    )
