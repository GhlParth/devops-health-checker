from devops_health_checker.schemas import (
    ToolParameter,
    ToolSchema,
)


def test_tool_parameter():
    parameter = ToolParameter(
        name="namespace",
        type="string",
        description="Kubernetes namespace",
        required=False,
        default=None,
    )

    assert parameter.name == "namespace"
    assert parameter.type == "string"
    assert parameter.required is False
    assert parameter.default is None


def test_tool_schema_without_parameters():
    schema = ToolSchema(
        name="aws_ec2_health",
        description="Check AWS EC2 health",
    )

    data = schema.to_dict()

    assert data["name"] == "aws_ec2_health"
    assert data["description"] == "Check AWS EC2 health"
    assert data["parameters"] == []


def test_tool_schema_with_parameters():
    schema = ToolSchema(
        name="kubernetes_health",
        description="Check Kubernetes health",
        parameters=[
            ToolParameter(
                name="namespace",
                type="string",
                description="Kubernetes namespace",
                required=False,
                default=None,
            )
        ],
    )

    data = schema.to_dict()

    assert data["name"] == "kubernetes_health"
    assert len(data["parameters"]) == 1

    parameter = data["parameters"][0]

    assert parameter["name"] == "namespace"
    assert parameter["type"] == "string"
    assert parameter["required"] is False
