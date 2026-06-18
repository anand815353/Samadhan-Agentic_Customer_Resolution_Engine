"""LangGraph workflow graph builder for Samadhan agent (T-051)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from app.agent.constants import ORDERED_WORKFLOW_NODES
from app.agent.nodes.registry import NodeRegistry, build_default_registry, validate_registry
from app.agent.state import AgentState

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

_compiled_default_graph: CompiledStateGraph | None = None


def build_agent_graph(*, registry: NodeRegistry | None = None) -> CompiledStateGraph:
    """Build and compile the linear Samadhan agent workflow graph."""
    node_registry = registry or build_default_registry()
    validate_registry(node_registry)

    builder = StateGraph(AgentState)
    for node_name in ORDERED_WORKFLOW_NODES:
        builder.add_node(node_name, node_registry[node_name])

    first_node = ORDERED_WORKFLOW_NODES[0]
    last_node = ORDERED_WORKFLOW_NODES[-1]
    builder.add_edge(START, first_node)

    for current, nxt in zip(ORDERED_WORKFLOW_NODES, ORDERED_WORKFLOW_NODES[1:]):
        builder.add_edge(current, nxt)

    builder.add_edge(last_node, END)
    return builder.compile()


def get_compiled_agent_graph(
    *,
    registry: NodeRegistry | None = None,
    force_rebuild: bool = False,
) -> CompiledStateGraph:
    """Return a compiled graph, caching the default registry build only."""
    global _compiled_default_graph

    if registry is not None:
        return build_agent_graph(registry=registry)

    if _compiled_default_graph is None or force_rebuild:
        _compiled_default_graph = build_agent_graph()
    return _compiled_default_graph


def get_registered_node_names(*, registry: NodeRegistry | None = None) -> tuple[str, ...]:
    """Return workflow node names present in a registry."""
    node_registry = registry or build_default_registry()
    validate_registry(node_registry)
    return ORDERED_WORKFLOW_NODES
