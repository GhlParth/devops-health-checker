from devops_health_checker.registry import (
    ToolRegistry,
)

from devops_health_checker.schemas import (
    ToolParameter,
    ToolSchema,
)

from devops_health_checker.tools.aws import (
    check_ec2_health,
)

from devops_health_checker.tools.github import (
    check_github_health,
)

from devops_health_checker.tools.kubernetes import (
    check_kubernetes_health,
)


def create_tool_registry():
    registry = ToolRegistry()

    aws_schema = ToolSchema(
        name="aws_ec2_health",
        description=(
            "Check the health and state of "
            "AWS EC2 instances."
        ),
    )

    github_schema = ToolSchema(
        name="github_repository",
        description=(
            "Check the health and information "
            "of a GitHub repository."
        ),
        parameters=[
            ToolParameter(
                name="owner",
                type="string",
                description=(
                    "GitHub repository owner "
                    "or organization."
                ),
                required=True,
            ),
            ToolParameter(
                name="repository",
                type="string",
                description=(
                    "GitHub repository name."
                ),
                required=True,
            ),
        ],
    )

    kubernetes_schema = ToolSchema(
        name="kubernetes_health",
        description=(
            "Check Kubernetes nodes and pods "
            "for health issues."
        ),
        parameters=[
            ToolParameter(
                name="namespace",
                type="string",
                description=(
                    "Kubernetes namespace to "
                    "inspect. If omitted, "
                    "all namespaces are checked."
                ),
                required=False,
                default=None,
            ),
        ],
    )

    registry.register(
        name="aws_ec2_health",
        description=aws_schema.description,
        function=check_ec2_health,
        schema=aws_schema,
    )

    registry.register(
        name="github_repository",
        description=github_schema.description,
        function=check_github_health,
        schema=github_schema,
    )

    registry.register(
        name="kubernetes_health",
        description=kubernetes_schema.description,
        function=check_kubernetes_health,
        schema=kubernetes_schema,
    )

    return registry