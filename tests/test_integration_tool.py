from devops_health_checker.execution import ToolExecutionResult
from devops_health_checker.registry import ToolRegistry
from devops_health_checker.schemas import ToolSchema
from devops_health_checker.tools.integration import (
    create_agentic_review_tool,
)


class MockRegistry:
    def __init__(self):
        self.calls = []

    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "search_devops_knowledge":
            return ToolExecutionResult(
                tool_name=name,
                success=True,
                result={"results": [{"source": "pods.md"}]},
            )
        return ToolExecutionResult(
            tool_name=name,
            success=True,
            result={
                "name": name,
                "status": "WARNING",
                "details": {"unhealthy_pods": 1},
                "errors": [],
            },
        )


def test_agentic_review_combines_health_and_guidance() -> None:
    registry = MockRegistry()
    review = create_agentic_review_tool(registry)

    result = review(
        ["kubernetes"],
        namespace="default",
        knowledge_query="pod restart",
    )

    assert result["components"] == ["kubernetes"]
    assert result["health_results"]["kubernetes"]["success"] is True
    assert result["guidance"] == [{"source": "pods.md"}]
    assert registry.calls == [
        ("kubernetes_health", {"namespace": "default"}),
        ("search_devops_knowledge", {"query": "pod restart", "top_k": 3}),
    ]


def test_agentic_review_rejects_unknown_components() -> None:
    review = create_agentic_review_tool(MockRegistry())

    try:
        review(["terraform"])
        assert False, "Expected unsupported component error"
    except ValueError as error:
        assert "Unsupported component" in str(error)


def test_agentic_review_requires_github_arguments() -> None:
    review = create_agentic_review_tool(MockRegistry())

    try:
        review(["github"])
        assert False, "Expected GitHub argument error"
    except ValueError as error:
        assert "owner and repository" in str(error)


def test_agentic_review_is_registered() -> None:
    from devops_health_checker.tools.registry import create_tool_registry

    registry = create_tool_registry()
    tool = registry.get("agentic_devops_review")

    assert isinstance(tool.schema, ToolSchema)
    assert tool.schema.parameters[0].name == "components"
