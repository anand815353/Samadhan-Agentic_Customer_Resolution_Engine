"""Injectable workflow node registry for graph construction."""

from __future__ import annotations

from app.agent.constants import ORDERED_WORKFLOW_NODES
from app.agent.intake_deps import get_default_intake_deps
from app.agent.intent_classifier_deps import get_default_intent_classifier_deps
from app.agent.retrieval_deps import get_default_retrieval_deps
from app.agent.guardrail_deps import get_default_guardrail_deps
from app.agent.resolution_planner_deps import get_default_resolution_planner_deps
from app.agent.response_deps import get_default_response_deps
from app.agent.audit_deps import get_default_audit_deps
from app.agent.ticket_update_deps import get_default_ticket_update_deps
from app.agent.tool_planner_deps import get_default_tool_planner_deps
from app.agent.nodes import audit, guardrail, intent_classifier, resolution_planner
from app.agent.nodes import response as response_node
from app.agent.nodes import retrieval, risk_classifier, ticket_router, ticket_update, tool_execution
from app.agent.nodes import tool_planner
from app.agent.nodes.base import NodeCallable, NodeRegistry
from app.agent.nodes.intake import build_intake_node
from app.agent.nodes.intent_classifier import build_intent_classifier_node
from app.agent.nodes.retrieval import build_retrieval_node
from app.agent.nodes.risk_classifier import build_risk_classifier_node
from app.agent.nodes.ticket_router import build_ticket_router_node
from app.agent.nodes.tool_planner import build_tool_planner_node
from app.agent.nodes.guardrail import build_guardrail_node
from app.agent.tool_execution_deps import get_default_tool_execution_deps
from app.agent.nodes.tool_execution import build_tool_execution_node
from app.agent.nodes.resolution_planner import build_resolution_planner_node
from app.agent.nodes.response import build_response_node
from app.agent.nodes.ticket_update import build_ticket_update_node
from app.agent.nodes.audit import build_audit_node

_DEFAULT_NODE_CALLABLES: dict[str, NodeCallable] = {
    "intent_classifier": intent_classifier.intent_classifier_node,
    "risk_classifier": risk_classifier.risk_classifier_node,
    "ticket_router": ticket_router.ticket_router_node,
    "retrieval": retrieval.retrieval_node,
    "tool_planner": tool_planner.tool_planner_node,
    "guardrail": guardrail.guardrail_node,
    "tool_execution": tool_execution.tool_execution_node,
    "resolution_planner": resolution_planner.resolution_planner_node,
    "response": response_node.response_node,
    "ticket_update": ticket_update.ticket_update_node,
    "audit": audit.audit_node,
}


def build_default_registry() -> NodeRegistry:
    """Return the default placeholder registry for all workflow nodes."""
    registry = dict(_DEFAULT_NODE_CALLABLES)
    registry["intake"] = build_intake_node(get_default_intake_deps())
    registry["intent_classifier"] = build_intent_classifier_node(get_default_intent_classifier_deps())
    registry["risk_classifier"] = build_risk_classifier_node()
    registry["ticket_router"] = build_ticket_router_node()
    registry["retrieval"] = build_retrieval_node(get_default_retrieval_deps())
    registry["tool_planner"] = build_tool_planner_node(get_default_tool_planner_deps())
    registry["guardrail"] = build_guardrail_node(get_default_guardrail_deps())
    registry["tool_execution"] = build_tool_execution_node(get_default_tool_execution_deps())
    registry["resolution_planner"] = build_resolution_planner_node(
        get_default_resolution_planner_deps(),
    )
    registry["response"] = build_response_node(get_default_response_deps())
    registry["ticket_update"] = build_ticket_update_node(get_default_ticket_update_deps())
    registry["audit"] = build_audit_node(get_default_audit_deps())
    return registry


def validate_registry(registry: NodeRegistry) -> None:
    """Ensure the registry contains every required workflow node."""
    missing = [name for name in ORDERED_WORKFLOW_NODES if name not in registry]
    if missing:
        raise ValueError(f"workflow registry missing nodes: {', '.join(missing)}")
