import pytest

from devops_health_checker.registry import (
    ToolRegistry,
)

from devops_health_checker.schemas import (
    ToolParameter,
    ToolSchema,
)


def create_test_schema(
    name="test",
):
    return ToolSchema(
        name=name,
        description="Test tool",
    )


def test_register_and_get_tool():
    registry = ToolRegistry()

    def test_function():
        return "hello"

    registry.register(
        name="test",
        description="Test tool",
        function=test_function,
        schema=create_test_schema(),
    )

    tool = registry.get("test")

    assert tool.name == "test"
    assert tool.description == "Test tool"
    assert tool.schema.name == "test"
    assert tool.function() == "hello"


def test_list_tools():
    registry = ToolRegistry()

    registry.register(
        name="tool_one",
        description="First tool",
        function=lambda: "one",
        schema=create_test_schema("tool_one"),
    )

    registry.register(
        name="tool_two",
        description="Second tool",
        function=lambda: "two",
        schema=create_test_schema("tool_two"),
    )

    tools = registry.list_tools()

    assert len(tools) == 2
    assert tools[0].name == "tool_one"
    assert tools[1].name == "tool_two"


def test_list_schemas():
    registry = ToolRegistry()

    registry.register(
        name="tool_one",
        description="First tool",
        function=lambda: "one",
        schema=create_test_schema("tool_one"),
    )

    schemas = registry.list_schemas()

    assert len(schemas) == 1
    assert schemas[0].name == "tool_one"


def test_duplicate_tool_registration():
    registry = ToolRegistry()

    registry.register(
        name="test",
        description="Test tool",
        function=lambda: "hello",
        schema=create_test_schema(),
    )

    with pytest.raises(ValueError):
        registry.register(
            name="test",
            description="Duplicate tool",
            function=lambda: "world",
            schema=create_test_schema(),
        )


def test_missing_tool():
    registry = ToolRegistry()

    with pytest.raises(KeyError):
        registry.get("does_not_exist")


def test_run_tool():
    registry = ToolRegistry()

    def test_function(value):
        return value * 2

    schema = ToolSchema(
        name="test",
        description="Test tool",
        parameters=[
            ToolParameter(
                name="value",
                type="integer",
                description="Value to multiply",
                required=True,
            )
        ],
    )

    registry.register(
        name="test",
        description="Test tool",
        function=test_function,
        schema=schema,
    )

    result = registry.run(
        "test",
        value=5,
    )

    assert result == 10


def test_invalid_arguments_do_not_execute_tool():
    registry = ToolRegistry()

    execution_count = {
        "count": 0
    }

    def dangerous_function(owner):
        execution_count["count"] += 1
        return "executed"

    schema = ToolSchema(
        name="dangerous_tool",
        description="Test validation boundary",
        parameters=[
            ToolParameter(
                name="owner",
                type="string",
                description="Owner",
                required=True,
            )
        ],
    )

    registry.register(
        name="dangerous_tool",
        description="Test validation boundary",
        function=dangerous_function,
        schema=schema,
    )

    with pytest.raises(
        Exception,
        match="Unknown parameter",
    ):
        registry.run(
            "dangerous_tool",
            owner="kubernetes",
            malicious="payload",
        )

    assert execution_count["count"] == 0