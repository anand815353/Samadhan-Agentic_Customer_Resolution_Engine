"""Validate tool-level audit references for workflow audit linkage."""

from __future__ import annotations

import re

from app.agent.exceptions import AuditNodeValidationError
from app.agent.state import AgentState, ToolStepState
from app.audit.id_generation import AUDIT_ID_PATTERN
from app.audit.services import AuditService

_AUDIT_ID_RE = re.compile(AUDIT_ID_PATTERN)
_EXECUTED_STATUSES = frozenset({"completed", "failed"})


async def collect_linked_tool_audit_ids(
    state: AgentState,
    audit_service: AuditService,
) -> list[str]:
    """Validate and return ordered, deduplicated tool audit IDs for executed steps."""
    linked: list[str] = []
    seen: set[str] = set()

    for step in state.tool_steps:
        if step.status not in _EXECUTED_STATUSES:
            continue
        audit_id = step.audit_id
        if not audit_id:
            raise AuditNodeValidationError(
                f"executed tool {step.tool_name} is missing audit_id",
            )
        if audit_id in seen:
            continue
        await _validate_tool_audit_reference(
            audit_service,
            audit_id=audit_id,
            step=step,
            state=state,
        )
        seen.add(audit_id)
        linked.append(audit_id)

    return linked


async def _validate_tool_audit_reference(
    audit_service: AuditService,
    *,
    audit_id: str,
    step: ToolStepState,
    state: AgentState,
) -> None:
    if not _AUDIT_ID_RE.match(audit_id):
        raise AuditNodeValidationError(f"invalid tool audit_id format: {audit_id}")

    try:
        event = await audit_service.get_event(audit_id)
    except Exception as exc:
        raise AuditNodeValidationError(f"tool audit not found: {audit_id}") from exc

    if event.event_type != "tool_called":
        raise AuditNodeValidationError(
            f"audit {audit_id} is not a tool_called event",
        )
    if state.ticket_id and event.ticket_id and event.ticket_id != state.ticket_id:
        raise AuditNodeValidationError(
            f"tool audit {audit_id} belongs to a different ticket",
        )
    if state.customer_id and event.customer_id and event.customer_id != state.customer_id:
        raise AuditNodeValidationError(
            f"tool audit {audit_id} belongs to a different customer",
        )
    if event.tool_called and event.tool_called != step.tool_name:
        raise AuditNodeValidationError(
            f"tool audit {audit_id} tool name mismatch",
        )
