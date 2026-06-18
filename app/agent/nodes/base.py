"""Shared placeholder node behavior for T-051 skeleton (replaced in T-052+)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.agent.state import AgentState

NodeCallable = Callable[[AgentState], Awaitable[dict[str, Any]]]
NodeRegistry = dict[str, NodeCallable]


async def passthrough_node(state: AgentState) -> dict[str, Any]:
    """Temporary pass-through placeholder; preserves state without side effects."""
    _ = state
    return {}
