"""Async agent workflow invocation service (T-051)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from app.agent.exceptions import (
    AgentWorkflowExecutionError,
    AgentWorkflowValidationError,
    IntakeAccessDeniedError,
    IntakePersistenceError,
    IntakeValidationError,
    RiskClassifierValidationError,
    TicketRouterValidationError,
    RetrievalValidationError,
    ToolPlannerValidationError,
    GuardrailValidationError,
    ToolExecutionValidationError,
    ResolutionPlannerValidationError,
    ResponseValidationError,
    TicketUpdateValidationError,
    TicketUpdatePersistenceError,
    AuditNodeValidationError,
    AuditNodePersistenceError,
)
from app.agent.graph import get_compiled_agent_graph
from app.agent.state import AgentState
from app.common.service import BaseService

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


def _validate_input_state(state: AgentState) -> AgentState:
    try:
        return AgentState.model_validate(state.model_dump())
    except ValidationError as exc:
        raise AgentWorkflowValidationError("Invalid workflow state.") from exc


def _coerce_output_state(result: Any) -> AgentState:
    if isinstance(result, AgentState):
        try:
            return AgentState.model_validate(result.model_dump())
        except ValidationError as exc:
            raise AgentWorkflowValidationError("Workflow returned invalid state.") from exc
    if isinstance(result, dict):
        try:
            return AgentState.from_graph_dict(result)
        except ValidationError as exc:
            raise AgentWorkflowValidationError("Workflow returned invalid state.") from exc
    raise AgentWorkflowExecutionError("Workflow returned an unexpected result type.")


class AgentWorkflowService(BaseService):
    """Invoke the compiled LangGraph workflow with validated state I/O."""

    def __init__(self, *, compiled_graph: CompiledStateGraph | None = None) -> None:
        self._compiled_graph = compiled_graph or get_compiled_agent_graph()

    async def invoke(self, state: AgentState) -> AgentState:
        validated = _validate_input_state(state)
        try:
            result = await self._compiled_graph.ainvoke(validated)
        except asyncio.CancelledError:
            raise
        except (IntakeValidationError, IntakeAccessDeniedError, RiskClassifierValidationError, TicketRouterValidationError, RetrievalValidationError, ToolPlannerValidationError, GuardrailValidationError, ToolExecutionValidationError, ResolutionPlannerValidationError, ResponseValidationError, TicketUpdateValidationError, AuditNodeValidationError) as exc:
            raise AgentWorkflowValidationError(exc.message) from exc
        except (IntakePersistenceError, TicketUpdatePersistenceError, AuditNodePersistenceError) as exc:
            raise AgentWorkflowExecutionError(exc.message) from exc
        except AgentWorkflowValidationError:
            raise
        except ValidationError as exc:
            raise AgentWorkflowValidationError("Invalid workflow state during execution.") from exc
        except AgentWorkflowExecutionError:
            raise
        except Exception as exc:
            raise AgentWorkflowExecutionError("Workflow execution failed.") from exc
        return _coerce_output_state(result)


def get_agent_workflow_service(
    *,
    compiled_graph: CompiledStateGraph | None = None,
) -> AgentWorkflowService:
    """Factory for the agent workflow service."""
    return AgentWorkflowService(compiled_graph=compiled_graph)
