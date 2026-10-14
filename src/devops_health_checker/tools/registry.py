from devops_health_checker.aiops import create_aiops_investigator
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
from devops_health_checker.tools.integration import (
    create_agentic_review_tool,
)
from devops_health_checker.tools.knowledge import (
    search_devops_knowledge,
)
from devops_health_checker.tools.kubernetes import (
    check_kubernetes_health,
)


def create_tool_registry():
    registry = ToolRegistry()

    aws_schema = ToolSchema(
        name="aws_ec2_health",
        description=("Check the health and state of AWS EC2 instances."),
    )

    github_schema = ToolSchema(
        name="github_repository",
        description=("Check the health and information of a GitHub repository."),
        parameters=[
            ToolParameter(
                name="owner",
                type="string",
                description=("GitHub repository owner or organization."),
                required=True,
            ),
            ToolParameter(
                name="repository",
                type="string",
                description=("GitHub repository name."),
                required=True,
            ),
        ],
    )

    kubernetes_schema = ToolSchema(
        name="kubernetes_health",
        description=("Check Kubernetes nodes and pods for health issues."),
        parameters=[
            ToolParameter(
                name="namespace",
                type="string",
                description=(
                    "Kubernetes namespace to inspect. If omitted, all namespaces are checked."
                ),
                required=False,
                default=None,
            ),
        ],
    )

    knowledge_schema = ToolSchema(
        name="search_devops_knowledge",
        description=(
            "Search the local DevOps knowledge base for "
            "troubleshooting guidance and runbook context."
        ),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description=("The DevOps or infrastructure question to search for."),
                required=True,
            ),
            ToolParameter(
                name="top_k",
                type="integer",
                description=("Maximum number of relevant knowledge chunks to return."),
                required=False,
                default=5,
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

    registry.register(
        name="search_devops_knowledge",
        description=knowledge_schema.description,
        function=search_devops_knowledge,
        schema=knowledge_schema,
    )

    review_schema = ToolSchema(
        name="agentic_devops_review",
        description=(
            "Run selected read-only infrastructure health checks and "
            "retrieve relevant DevOps guidance."
        ),
        parameters=[
            ToolParameter(
                name="components",
                type="array",
                description=("Components to inspect: aws, kubernetes, or github."),
                required=True,
            ),
            ToolParameter(
                name="namespace",
                type="string",
                description="Optional Kubernetes namespace.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="owner",
                type="string",
                description="GitHub repository owner when github is selected.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="repository",
                type="string",
                description="GitHub repository when github is selected.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="knowledge_query",
                type="string",
                description="Optional explicit troubleshooting query.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="top_k",
                type="integer",
                description="Maximum number of guidance chunks.",
                required=False,
                default=3,
            ),
        ],
    )

    registry.register(
        name="agentic_devops_review",
        description=review_schema.description,
        function=create_agentic_review_tool(registry),
        schema=review_schema,
    )

    aiops_schema = ToolSchema(
        name="aiops_investigate",
        description=(
            "Detect health anomalies, triage incidents, and produce "
            "approval-gated remediation proposals without executing them."
        ),
        parameters=review_schema.parameters,
    )

    registry.register(
        name="aiops_investigate",
        description=aiops_schema.description,
        function=create_aiops_investigator(registry),
        schema=aiops_schema,
    )

    return registry
