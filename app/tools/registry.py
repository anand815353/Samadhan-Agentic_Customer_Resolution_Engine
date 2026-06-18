"""Canonical mock-tool registry for workflow execution (T-059)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from app.tools.base import BaseMockTool
from app.tools.constants import ALL_TOOL_NAMES, ToolName


class MockToolRegistry(Protocol):
    """Resolve registered mock tools by canonical name only."""

    def get(self, tool_name: ToolName) -> BaseMockTool: ...

    def contains(self, tool_name: ToolName) -> bool: ...


class FrozenMockToolRegistry:
    """Immutable name-to-tool mapping; no dynamic imports or substitution."""

    def __init__(self, tools: Mapping[ToolName, BaseMockTool]) -> None:
        missing = [name for name in ALL_TOOL_NAMES if name not in tools]
        if missing:
            raise ValueError(f"mock tool registry missing tools: {', '.join(missing)}")
        self._tools: dict[ToolName, BaseMockTool] = dict(tools)

    def contains(self, tool_name: ToolName) -> bool:
        return tool_name in self._tools

    def get(self, tool_name: ToolName) -> BaseMockTool:
        if tool_name not in self._tools:
            raise KeyError(f"unregistered tool: {tool_name}")
        return self._tools[tool_name]
