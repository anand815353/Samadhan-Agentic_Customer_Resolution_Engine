"""Build validated ToolInput objects for planned workflow steps (T-057)."""

from __future__ import annotations

from typing import Any

from app.agent.planning.tool_plan_types import ToolPlanStep
from app.agent.state import AgentState
from app.tickets.constants import TicketIntent
from app.tools.constants import ToolName
from app.tools.schemas import ToolInput

_DOCUMENT_TYPE_BY_INTENT: dict[TicketIntent, str] = {
    "loan_statement_request": "loan_statement",
    "noc_closure_certificate": "noc",
}


def _first_loan_id(state: AgentState) -> str | None:
    if state.customer_context is None:
        return None
    if not state.customer_context.loan_ids:
        return None
    return state.customer_context.loan_ids[0]


def _policy_rag_parameters(state: AgentState) -> dict[str, Any]:
    query = (state.normalized_message or state.customer_message).strip()
    parameters: dict[str, Any] = {"query": query}
    if state.retrieval is not None and state.retrieval.result is not None:
        domain = state.retrieval.result.applied_domain_filter
        if domain:
            parameters["domain"] = domain
    return parameters


def _document_generation_parameters(
    intent: TicketIntent,
    *,
    document_type: str | None,
    state: AgentState,
) -> dict[str, Any]:
    resolved_type = document_type or _DOCUMENT_TYPE_BY_INTENT.get(intent)
    if resolved_type is None:
        return {}
    parameters: dict[str, Any] = {"document_type": resolved_type}
    loan_id = _first_loan_id(state)
    if loan_id is not None:
        parameters["loan_id"] = loan_id
    return parameters


def _loan_scoped_parameters(state: AgentState) -> dict[str, Any]:
    loan_id = _first_loan_id(state)
    if loan_id is None:
        return {}
    return {"loan_id": loan_id}


def build_tool_parameters(
    tool_name: ToolName,
    intent: TicketIntent,
    *,
    step: ToolPlanStep,
    state: AgentState,
) -> dict[str, Any]:
    """Return safe bounded parameters for a planned tool step."""
    if tool_name == "PolicyRAGTool":
        return _policy_rag_parameters(state)
    if tool_name == "DocumentGenerationTool":
        return _document_generation_parameters(
            intent,
            document_type=step.document_type,
            state=state,
        )
    if tool_name in {"LoanStatusTool", "RepaymentTool"}:
        return _loan_scoped_parameters(state)
    if tool_name == "RMRedirectTool":
        return {"request_callback": True}
    return {}


def build_tool_input(
    step: ToolPlanStep,
    *,
    intent: TicketIntent,
    state: AgentState,
) -> ToolInput:
    """Construct a validated ToolInput for one planned step."""
    if state.customer_id is None:
        raise ValueError("customer_id is required to build tool input")
    if state.ticket_id is None:
        raise ValueError("ticket_id is required to build tool input")

    parameters = build_tool_parameters(
        step.tool_name,
        intent,
        step=step,
        state=state,
    )
    return ToolInput(
        customer_id=state.customer_id,
        ticket_id=state.ticket_id,
        intent=intent,
        parameters=parameters,
        request_id=state.workflow_id,
        actor="system",
    )
