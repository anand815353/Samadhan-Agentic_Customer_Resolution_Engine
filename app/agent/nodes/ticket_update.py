"""LangGraph ticket update node implementation (T-062)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agent.exceptions import TicketUpdatePersistenceError, TicketUpdateValidationError
from app.agent.nodes.base import NodeCallable
from app.agent.persistence.persistence_types import WorkflowTicketUpdateCommand
from app.agent.state import AgentState, TicketUpdateState
from app.agent.ticket_update_deps import TicketUpdateDeps

logger = logging.getLogger("samadhan.agent")


class TicketUpdateNode:
    """Persist workflow outcomes to tickets and messages."""

    def __init__(self, deps: TicketUpdateDeps) -> None:
        self._deps = deps
        self._service = deps.workflow_ticket_update_service

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        if state.resolution_plan is None:
            raise TicketUpdateValidationError("resolution_plan is required")
        if not state.customer_response or not state.customer_response.strip():
            raise TicketUpdateValidationError("customer_response is required")
        if state.customer_response_metadata is None:
            raise TicketUpdateValidationError("customer_response_metadata is required")

        command = WorkflowTicketUpdateCommand(
            state=state,
            resolution_plan=state.resolution_plan,
            customer_response=state.customer_response,
            customer_response_metadata=state.customer_response_metadata,
        )

        try:
            result = await self._service.persist(command)
        except TicketUpdateValidationError:
            raise
        except TicketUpdatePersistenceError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise TicketUpdatePersistenceError("ticket update persistence failed") from exc

        ticket_update = TicketUpdateState(
            ticket_status=result.ticket_status,
            service_request_id=result.service_request_id,
            update_summary=result.update_summary,
            document_path=result.document_path,
            ai_message_id=result.ai_message_id,
            previous_ticket_class=result.previous_ticket_class,
            persisted_ticket_class=result.persisted_ticket_class,
            previous_status=result.previous_status,
            human_review_queued=result.human_review_queued,
            idempotent_replay=result.idempotent_replay,
        )

        logger.info(
            "ticket update ready workflow_id=%s ticket_id=%s status=%s hr_queued=%s",
            state.workflow_id,
            state.ticket_id,
            result.ticket_status,
            result.human_review_queued,
        )
        return {"ticket_update": ticket_update}


def build_ticket_update_node(deps: TicketUpdateDeps) -> NodeCallable:
    """Return a ticket update node callable."""
    node = TicketUpdateNode(deps)

    async def ticket_update_node(state: AgentState) -> dict[str, Any]:
        return await node(state)

    return ticket_update_node


from app.agent.nodes.base import passthrough_node as ticket_update_node  # noqa: E402

__all__ = ["TicketUpdateNode", "build_ticket_update_node", "ticket_update_node"]
