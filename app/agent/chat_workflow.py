"""Chat-facing workflow facade for future customer chat routes (T-051)."""

from __future__ import annotations

from app.agent.state import AgentState
from app.agent.workflow_service import AgentWorkflowService, get_agent_workflow_service
from app.common.service import BaseService


class CustomerChatWorkflowService(BaseService):
    """Thin facade callable from future T-065 customer chat routes."""

    def __init__(self, workflow_service: AgentWorkflowService) -> None:
        self._workflow_service = workflow_service

    async def process_customer_message(
        self,
        *,
        workflow_id: str,
        user_id: str,
        customer_message: str,
    ) -> AgentState:
        initial_state = AgentState.initial(
            workflow_id=workflow_id,
            user_id=user_id,
            customer_message=customer_message,
        )
        return await self._workflow_service.invoke(initial_state)


def get_customer_chat_workflow_service(
    *,
    workflow_service: AgentWorkflowService | None = None,
) -> CustomerChatWorkflowService:
    """Factory for the customer chat workflow facade."""
    service = workflow_service or get_agent_workflow_service()
    return CustomerChatWorkflowService(service)
