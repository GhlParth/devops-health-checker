from devops_health_checker.execution import (
    ToolExecutor,
)
from devops_health_checker.models import (
    HealthResult,
    HealthStatus,
)
from devops_health_checker.registry import (
    Tool,
)
from devops_health_checker.schemas import (
    ToolParameter,
    ToolSchema,
)


def test_successful_tool_execution():
    def test_function(value):
        return value * 2

    schema = ToolSchema(
        name="test",
        description="Test tool",
        parameters=[
            ToolParameter(
                name="value",
                type="integer",
                description="Value",
                required=True,
            )
        ],
    )

    tool = Tool(
        name="test",
        description="Test tool",
        function=test_function,
        schema=schema,
    )

    executor = ToolExecutor()

    result = executor.execute(
        tool,
        {
            "value": 5,
        },
    )

    assert result.tool_name == "test"
    assert result.success is True
    assert result.result == 10
    assert result.error is None
    assert result.duration_ms >= 0


def test_invalid_arguments_are_not_executed():
    execution_count = {"count": 0}

    def test_function(value):
        execution_count["count"] += 1
        return value

    schema = ToolSchema(
        name="test",
        description="Test tool",
        parameters=[
            ToolParameter(
                name="value",
                type="integer",
                description="Value",
                required=True,
            )
        ],
    )

    tool = Tool(
        name="test",
        description="Test tool",
        function=test_function,
        schema=schema,
    )

    executor = ToolExecutor()

    result = executor.execute(
        tool,
        {
            "unknown": 10,
        },
    )

    assert result.success is False
    assert result.result is None
    assert "Unknown parameter" in result.error
    assert execution_count["count"] == 0


def test_tool_execution_error_is_captured():
    def failing_function():
        raise RuntimeError("Something went wrong")

    schema = ToolSchema(
        name="failing_tool",
        description="Failing tool",
    )

    tool = Tool(
        name="failing_tool",
        description="Failing tool",
        function=failing_function,
        schema=schema,
    )

    executor = ToolExecutor()

    result = executor.execute(
        tool,
        {},
    )

    assert result.success is False
    assert result.result is None
    assert result.error == ("Something went wrong")
    assert result.duration_ms >= 0


def test_health_result_is_preserved():
    health_result = HealthResult(
        name="test",
        status=HealthStatus.HEALTHY,
        details={"message": "Everything is healthy"},
    )

    def health_function():
        return health_result

    schema = ToolSchema(
        name="health_tool",
        description="Health tool",
    )

    tool = Tool(
        name="health_tool",
        description="Health tool",
        function=health_function,
        schema=schema,
    )

    executor = ToolExecutor()

    result = executor.execute(
        tool,
        {},
    )

    assert result.success is True
    assert result.result is health_result
    assert result.result.status == (HealthStatus.HEALTHY)


def test_execution_result_to_dict():
    health_result = HealthResult(
        name="test",
        status=HealthStatus.WARNING,
        details={"message": "Something needs attention"},
        errors=[],
    )

    def health_function():
        return health_result

    schema = ToolSchema(
        name="health_tool",
        description="Health tool",
    )

    tool = Tool(
        name="health_tool",
        description="Health tool",
        function=health_function,
        schema=schema,
    )

    executor = ToolExecutor()

    result = executor.execute(
        tool,
        {},
    )

    data = result.to_dict()

    assert data["tool_name"] == "health_tool"
    assert data["success"] is True
    assert data["result"]["name"] == "test"
    assert data["result"]["status"] == "WARNING"
    assert data["duration_ms"] >= 0
