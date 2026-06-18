"""Mock tool input/output schemas aligned with MOCK_TOOLS_SPEC §3."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.tickets.constants import TicketIntent, TransitionActor
from app.tools.constants import ToolErrorCode, ToolName


class ToolInput(BaseModel):
    """Common structured input for all mock tools."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: str = Field(..., pattern=r"^CUST-\d{3}$")
    ticket_id: str = Field(..., pattern=r"^TKT-\d{4}-\d{4}$")
    intent: TicketIntent
    parameters: dict[str, Any] = Field(default_factory=dict)
    request_id: str = Field(..., min_length=1)
    actor: TransitionActor


class ToolError(BaseModel):
    """Controlled error object returned in tool output on failure."""

    model_config = ConfigDict(str_strip_whitespace=True)

    code: ToolErrorCode
    message: str = Field(..., min_length=1)
    retryable: bool = False
    details: dict[str, Any] | None = None


class ToolOutput(BaseModel):
    """Common structured output for all mock tools."""

    model_config = ConfigDict(str_strip_whitespace=True)

    success: bool
    tool_name: str
    data: dict[str, Any] = Field(default_factory=dict)
    customer_safe_summary: str
    action_taken: str
    escalation_required: bool
    service_request_id: str | None = Field(default=None, pattern=r"^SR-\d{4}-\d{4}$")
    audit_id: str | None = Field(default=None, pattern=r"^AUD-\d{4}-\d{4}$")
    error: ToolError | None = None


class ToolRunResult(BaseModel):
    """Internal result from subclass _run(); not part of the public API contract."""

    model_config = ConfigDict(str_strip_whitespace=True)

    data: dict[str, Any] = Field(default_factory=dict)
    customer_safe_summary: str = Field(..., min_length=1)
    action_taken: str = Field(..., min_length=1)
    escalation_required: bool = False
    service_request_id: str | None = Field(default=None, pattern=r"^SR-\d{4}-\d{4}$")
