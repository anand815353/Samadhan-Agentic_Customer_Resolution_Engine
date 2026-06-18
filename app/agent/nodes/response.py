"""LangGraph response node implementation (T-061)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agent.exceptions import ResponseValidationError
from app.agent.nodes.base import NodeCallable
from app.agent.response.response_generation_service import ResponseGenerationService
from app.agent.response.response_types import RESPONSE_PROMPT_VERSION
from app.agent.response_deps import ResponseDeps
from app.agent.state import AgentState, CustomerResponseMetadata

logger = logging.getLogger("samadhan.agent")


class ResponseNode:
    """Generate a validated customer-safe response from the resolution plan."""

    def __init__(self, deps: ResponseDeps) -> None:
        self._service = ResponseGenerationService(deps)
        self._deps = deps

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        if self._deps.policy_version != RESPONSE_PROMPT_VERSION:
            raise ResponseValidationError("response prompt policy version mismatch")

        try:
            result = await self._service.generate(state)
        except ResponseValidationError:
            raise
        except asyncio.CancelledError:
            raise
        except ValueError as exc:
            raise ResponseValidationError(str(exc)) from exc

        metadata = CustomerResponseMetadata(
            generation_source=result.generation_source,
            prompt_version=result.prompt_version,
            safety_status=result.safety_status,
            referenced_ticket_id=result.referenced_ticket_id,
            referenced_service_request_ids=list(result.referenced_service_request_ids),
            referenced_source_ids=list(result.referenced_source_ids),
            fallback_reason=result.fallback_reason,
            mock_disclaimer_included=result.mock_disclaimer_included,
        )

        logger.info(
            "response ready workflow_id=%s ticket_id=%s source=%s safety=%s length=%s",
            state.workflow_id,
            result.referenced_ticket_id,
            result.generation_source,
            result.safety_status,
            len(result.response_text),
        )
        return {
            "customer_response": result.response_text,
            "customer_response_metadata": metadata,
        }


def build_response_node(deps: ResponseDeps) -> NodeCallable:
    """Return a response node callable."""
    node = ResponseNode(deps)

    async def response_node(state: AgentState) -> dict[str, Any]:
        return await node(state)

    return response_node


from app.agent.nodes.base import passthrough_node as response_node  # noqa: E402

__all__ = ["ResponseNode", "build_response_node", "response_node"]
