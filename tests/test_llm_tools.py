from devops_health_checker.llm_tools import (
    registry_to_openrouter_tools,
    schema_to_openrouter_tool,
)
from devops_health_checker.schemas import (
    ToolParameter,
    ToolSchema,
)


def test_schema_to_openrouter_tool_without_parameters():
    schema = ToolSchema(
        name="aws_ec2_health",
        description="Check AWS EC2 health.",
    )

    result = schema_to_openrouter_tool(schema)

    assert result["type"] == "function"

    function = result["function"]

    assert function["name"] == (
        "aws_ec2_health"
    )

    assert function["description"] == (
        "Check AWS EC2 health."
    )

    assert function["parameters"]["type"] == (
        "object"
    )

    assert function["parameters"]["properties"] == {}

    assert function["parameters"]["required"] == []


def test_schema_to_openrouter_tool_with_parameters():
    schema = ToolSchema(
        name="github_repository",
        description="Check a GitHub repository.",
        parameters=[
            ToolParameter(
                name="owner",
                type="string",
                description="Repository owner.",
                required=True,
            ),
            ToolParameter(
                name="repository",
                type="string",
                description="Repository name.",
                required=True,
            ),
        ],
    )

    result = schema_to_openrouter_tool(schema)

    function = result["function"]

    properties = (
        function["parameters"]["properties"]
    )

    assert properties["owner"]["type"] == (
        "string"
    )

    assert properties["owner"]["description"] == (
        "Repository owner."
    )

    assert properties["repository"]["type"] == (
        "string"
    )

    assert properties["repository"]["description"] == (
        "Repository name."
    )

    assert function["parameters"]["required"] == [
        "owner",
        "repository",
    ]


def test_schema_to_openrouter_tool_with_optional_default():
    schema = ToolSchema(
        name="kubernetes_health",
        description="Check Kubernetes health.",
        parameters=[
            ToolParameter(
                name="namespace",
                type="string",
                description="Kubernetes namespace.",
                required=False,
                default=None,
            ),
        ],
    )

    result = schema_to_openrouter_tool(schema)

    function = result["function"]

    properties = (
        function["parameters"]["properties"]
    )

    assert properties["namespace"]["type"] == (
        "string"
    )

    assert "default" not in properties[
        "namespace"
    ]

    assert function["parameters"]["required"] == []


def test_schema_to_openrouter_tool_preserves_default():
    schema = ToolSchema(
        name="test_tool",
        description="Test tool.",
        parameters=[
            ToolParameter(
                name="environment",
                type="string",
                description="Environment name.",
                required=False,
                default="production",
            ),
        ],
    )

    result = schema_to_openrouter_tool(schema)

    parameter = (
        result["function"]["parameters"][
            "properties"
        ]["environment"]
    )

    assert parameter["default"] == "production"


def test_registry_to_openrouter_tools():
    class MockTool:
        def __init__(self, schema):
            self.schema = schema

    class MockRegistry:
        def list_tools(self):
            return [
                MockTool(
                    ToolSchema(
                        name="tool_one",
                        description="First tool.",
                    )
                ),
                MockTool(
                    ToolSchema(
                        name="tool_two",
                        description="Second tool.",
                    )
                ),
            ]

    result = registry_to_openrouter_tools(
        MockRegistry()
    )

    assert len(result) == 2

    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == (
        "tool_one"
    )

    assert result[1]["type"] == "function"
    assert result[1]["function"]["name"] == (
        "tool_two"
    )