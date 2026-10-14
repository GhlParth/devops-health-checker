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


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        function: Callable[..., Any],
        schema: ToolSchema,
    ):
        if name in self._tools:
            raise ValueError(
                f"Tool already registered: {name}"
            )

        self._tools[name] = Tool(
            name=name,
            description=description,
            function=function,
            schema=schema,
        )

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(
                f"Tool not found: {name}"
            )

        return self._tools[name]

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def list_schemas(self) -> list[ToolSchema]:
        return [
            tool.schema
            for tool in self._tools.values()
        ]

    def execute(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ):
        from devops_health_checker.execution import (
            ToolExecutor,
        )

        tool = self.get(name)

        executor = ToolExecutor()

        return executor.execute(
            tool,
            arguments,
        )

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
                raise ToolValidationError(
                    execution.error
                )

            raise RuntimeError(
                f"Tool execution failed: {name}"
            )

        return execution.result