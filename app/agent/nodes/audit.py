"""LangGraph audit node implementation (T-063)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agent.audit_deps import AuditDeps
from app.agent.exceptions import AuditNodePersistenceError, AuditNodeValidationError
from app.agent.nodes.base import NodeCallable
from app.agent.state import AgentState, WorkflowAuditState
from app.agent.workflow_audit.workflow_audit_types import WorkflowAuditCommand

logger = logging.getLogger("samadhan.agent")


class AuditNode:
    """Persist one consolidated workflow audit after ticket update."""

    def __init__(self, deps: AuditDeps) -> None:
        self._deps = deps
        self._service = deps.workflow_audit_service

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        command = WorkflowAuditCommand(state=state)
        try:
            result = await self._service.persist(command)
        except AuditNodeValidationError:
            raise
        except AuditNodePersistenceError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise AuditNodePersistenceError("workflow audit persistence failed") from exc

        workflow_audit = WorkflowAuditState(
            workflow_audit_id=result.workflow_audit_id,
            event_type="workflow_completed",
            linked_tool_audit_ids=list(result.linked_tool_audit_ids),
            langsmith_trace_id=result.langsmith_trace_id,
            workflow_status="completed",
            idempotent_replay=result.idempotent_replay,
        )

        logger.info(
            "audit ready workflow_id=%s audit_id=%s replay=%s",
            state.workflow_id,
            result.workflow_audit_id,
            result.idempotent_replay,
        )
        return {"workflow_audit": workflow_audit}


def build_audit_node(deps: AuditDeps) -> NodeCallable:
    """Return an audit node callable."""
    node = AuditNode(deps)

    async def audit_node(state: AgentState) -> dict[str, Any]:
        return await node(state)

    return audit_node


from app.agent.nodes.base import passthrough_node as audit_node  # noqa: E402

__all__ = ["AuditNode", "build_audit_node", "audit_node"]
