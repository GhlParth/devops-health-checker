import time
from dataclasses import dataclass
from typing import Any

from devops_health_checker.models import (
    HealthResult,
)
from devops_health_checker.registry import (
    Tool,
)
from devops_health_checker.validation import (
    validate_tool_arguments,
)


@dataclass
class ToolExecutionResult:
    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0

    def to_dict(self):
        result_data = None

        if isinstance(
            self.result,
            HealthResult,
        ):
            result_data = self.result.to_dict()

        elif hasattr(
            self.result,
            "to_dict",
        ):
            result_data = self.result.to_dict()

        else:
            result_data = self.result

        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": result_data,
            "error": self.error,
            "duration_ms": round(
                self.duration_ms,
                2,
            ),
        }


class ToolExecutor:
    def execute(
        self,
        tool: Tool,
        arguments: dict[str, Any] | None = None,
    ) -> ToolExecutionResult:
        """
        Validate and execute a tool.
        """

        # -------------------------------------------------
        # 1. Validate arguments
        # -------------------------------------------------

        try:
            validated_arguments = (
                validate_tool_arguments(
                    tool.schema,
                    arguments,
                )
            )

        except Exception as error:
            return ToolExecutionResult(
                tool_name=tool.name,
                success=False,
                result=None,
                error=str(error),
                duration_ms=0.0,
            )

        # -------------------------------------------------
        # 2. Execute tool
        # -------------------------------------------------

        start = time.perf_counter()

        try:
            result = tool.function(
                **validated_arguments
            )

        except Exception as error:
            duration_ms = (
                time.perf_counter() - start
            ) * 1000

            return ToolExecutionResult(
                tool_name=tool.name,
                success=False,
                result=None,
                error=str(error),
                duration_ms=duration_ms,
            )

        duration_ms = (
            time.perf_counter() - start
        ) * 1000

        return ToolExecutionResult(
            tool_name=tool.name,
            success=True,
            result=result,
            error=None,
            duration_ms=duration_ms,
        )