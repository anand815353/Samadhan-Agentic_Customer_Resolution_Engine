"""Ordered mock-tool plan executor (T-059)."""

from __future__ import annotations

import asyncio
import logging
import time

from pydantic import ValidationError

from app.agent.exceptions import ToolExecutionValidationError
from app.agent.execution.authorization_validator import (
    step_execution_category,
    validate_execution_prerequisites,
    validate_step_authorization,
)
from app.agent.execution.condition_evaluator import should_execute_conditional_step
from app.agent.execution.execution_types import ToolPlanExecutionResult
from app.agent.state import AgentState, ToolStepState, WorkflowError
from app.tools.registry import MockToolRegistry
from app.tools.schemas import ToolError, ToolOutput

logger = logging.getLogger("samadhan.agent")


class ToolPlanExecutor:
    """Execute T-058-authorized mock tools in deterministic T-057 order."""

    def __init__(
        self,
        registry: MockToolRegistry,
        *,
        tool_timeout_seconds: float = 30.0,
    ) -> None:
        self._registry = registry
        self._tool_timeout_seconds = tool_timeout_seconds

    async def execute(self, state: AgentState) -> ToolPlanExecutionResult:
        guardrail = validate_execution_prerequisites(state)
        if not state.tool_steps:
            return ToolPlanExecutionResult(
                tool_steps=[],
                audit_event_ids=list(state.audit_event_ids),
            )

        updated_steps: list[ToolStepState] = []
        audit_event_ids = list(state.audit_event_ids)
        workflow_errors = list(state.workflow_errors)
        running_steps = [step.model_copy() for step in state.tool_steps]

        for index, step in enumerate(running_steps):
            category = step_execution_category(index, guardrail=guardrail)

            if category == "blocked":
                updated_steps.append(step.model_copy(update={"status": "skipped"}))
                continue

            if category == "unapproved":
                updated_steps.append(step.model_copy(update={"status": "skipped"}))
                continue

            if category == "conditional":
                condition = step.planner_condition
                if not condition or not should_execute_conditional_step(
                    condition,
                    step_index=index,
                    tool_steps=updated_steps,
                ):
                    updated_steps.append(step.model_copy(update={"status": "skipped"}))
                    continue

            try:
                validate_step_authorization(
                    state.model_copy(update={"tool_steps": running_steps}),
                    index,
                    guardrail=guardrail,
                    registry=self._registry,
                )
            except ToolExecutionValidationError as exc:
                raise exc

            tool = self._registry.get(step.tool_name)
            assert step.tool_input is not None
            started = time.perf_counter()

            try:
                raw_output = await asyncio.wait_for(
                    tool.execute(step.tool_input, validate_links=False),
                    timeout=self._tool_timeout_seconds,
                )
            except asyncio.TimeoutError:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                logger.warning(
                    "tool execution timed out workflow_id=%s step=%s tool=%s elapsed_ms=%s",
                    state.workflow_id,
                    index,
                    step.tool_name,
                    elapsed_ms,
                )
                failure = ToolOutput(
                    success=False,
                    tool_name=step.tool_name,
                    customer_safe_summary="The tool request timed out before completion.",
                    action_taken="execution_timed_out",
                    escalation_required=guardrail.escalation_required,
                    error=ToolError(
                        code="execution_failed",
                        message="Tool execution timed out.",
                        retryable=False,
                    ),
                )
                updated_steps.append(
                    step.model_copy(update={"status": "failed", "tool_output": failure}),
                )
                workflow_errors.append(
                    WorkflowError(
                        code="tool_failed",
                        message=f"Tool {step.tool_name} timed out.",
                        node="tool_execution",
                        recoverable=True,
                    ),
                )
                continue
            except asyncio.CancelledError:
                raise

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            try:
                output = ToolOutput.model_validate(raw_output.model_dump())
            except ValidationError as exc:
                raise ToolExecutionValidationError(
                    f"tool {step.tool_name} returned malformed output",
                ) from exc

            if output.tool_name != step.tool_name:
                failure = ToolOutput(
                    success=False,
                    tool_name=step.tool_name,
                    customer_safe_summary="The tool response could not be validated safely.",
                    action_taken="output_validation_failed",
                    escalation_required=guardrail.escalation_required,
                    error=ToolError(
                        code="execution_failed",
                        message="Returned tool name does not match executed tool.",
                        retryable=False,
                    ),
                )
                updated_steps.append(
                    step.model_copy(
                        update={
                            "status": "failed",
                            "tool_output": failure,
                        },
                    ),
                )
                running_steps[index] = updated_steps[-1]
                continue

            status = "completed" if output.success else "failed"
            step_result = step.model_copy(
                update={
                    "status": status,
                    "tool_output": output,
                    "audit_id": output.audit_id,
                },
            )
            updated_steps.append(step_result)
            running_steps[index] = step_result

            if output.audit_id and output.audit_id not in audit_event_ids:
                audit_event_ids.append(output.audit_id)

            logger.info(
                "tool executed workflow_id=%s ticket_id=%s step=%s tool=%s status=%s "
                "success=%s audit_id=%s escalation=%s elapsed_ms=%s",
                state.workflow_id,
                state.ticket_id,
                index,
                step.tool_name,
                status,
                output.success,
                output.audit_id,
                output.escalation_required,
                elapsed_ms,
            )

        return ToolPlanExecutionResult(
            tool_steps=updated_steps,
            audit_event_ids=audit_event_ids,
            workflow_errors=workflow_errors if workflow_errors != list(state.workflow_errors) else None,
        )
