from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from devops_health_checker.schemas import (
    ToolSchema,
)


@dataclass
class Tool:
    name: str
    description: str
    function: Callable[..., Any]
    schema: ToolSchema
    read_only: bool = True
    requires_approval: bool = False


class ToolRegistry:
    def __init__(self, audit_log=None, metrics=None):
        self._tools: dict[str, Tool] = {}
        from devops_health_checker.observability import MetricsCollector
        from devops_health_checker.security import AuditLog

        self.audit_log = audit_log or AuditLog()
        self.metrics = metrics or MetricsCollector()

    def register(
        self,
        name: str,
        description: str,
        function: Callable[..., Any],
        schema: ToolSchema,
        read_only: bool = True,
        requires_approval: bool = False,
    ):
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")

        self._tools[name] = Tool(
            name=name,
            description=description,
            function=function,
            schema=schema,
            read_only=read_only,
            requires_approval=requires_approval,
        )

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")

        return self._tools[name]

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def list_schemas(self) -> list[ToolSchema]:
        return [tool.schema for tool in self._tools.values()]

    def execute(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        approved: bool = False,
    ):
        from devops_health_checker.execution import (
            ToolExecutor,
        )

        tool = self.get(name)

        from devops_health_checker.security import validate_tool_policy

        try:
            validate_tool_policy(tool, approved)
        except PermissionError as error:
            self.audit_log.record(
                event="tool_denied",
                tool_name=name,
                success=False,
                arguments=arguments,
                error=str(error),
            )
            from devops_health_checker.execution import ToolExecutionResult

            return ToolExecutionResult(
                tool_name=name,
                success=False,
                error=str(error),
            )

        executor = ToolExecutor()

        execution = executor.execute(
            tool,
            arguments,
        )
        self.audit_log.record(
            event="tool_executed",
            tool_name=name,
            success=execution.success,
            arguments=arguments,
            error=execution.error,
        )
        self.metrics.record_tool(execution)
        return execution

    def run(
        self,
        name: str,
        **kwargs,
    ):
        """
        Backward-compatible direct execution.

        Returns the underlying tool result.

        Use execute() when the caller needs the
        structured ToolExecutionResult.
        """

        execution = self.execute(
            name,
            kwargs,
        )

        if not execution.success:
            from devops_health_checker.validation import (
                ToolValidationError,
            )

            if execution.error:
                raise ToolValidationError(execution.error)

            raise RuntimeError(f"Tool execution failed: {name}")

        return execution.result
