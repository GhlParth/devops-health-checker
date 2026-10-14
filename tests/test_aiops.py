from devops_health_checker.aiops import create_aiops_investigator
from devops_health_checker.execution import ToolExecutionResult


class MockRegistry:
    def __init__(self, result):
        self.result = result

    def execute(self, name, arguments):
        if name == "search_devops_knowledge":
            return ToolExecutionResult(
                tool_name=name,
                success=True,
                result={"results": [{"source": "pods.md"}]},
            )
        return ToolExecutionResult(
            tool_name=name,
            success=True,
            result=self.result,
        )


def test_aiops_triages_anomaly_and_only_proposes_actions():
    registry = MockRegistry(
        {
            "name": "kubernetes",
            "status": "CRITICAL",
            "details": {"unhealthy_pods": 2},
            "errors": [],
        }
    )

    result = create_aiops_investigator(registry)(
        ["kubernetes"],
        knowledge_query="pod restart",
    )

    assert result["incidents"][0]["severity"] == "critical"
    assert result["guidance"] == [{"source": "pods.md"}]
    assert result["automation"]["enabled"] is False
    assert result["automation"]["executed_actions"] == []
    assert all(
        proposal["requires_approval"] and not proposal["executed"]
        for proposal in result["proposals"]
    )


def test_aiops_ignores_healthy_components():
    registry = MockRegistry(
        {"name": "aws", "status": "HEALTHY", "details": {}, "errors": []}
    )

    result = create_aiops_investigator(registry)(["aws"])

    assert result["incidents"] == []
    assert result["proposals"] == []


def test_aiops_provider_failure_is_tracked():
    class FailingRegistry:
        def execute(self, name, arguments):
            if name == "search_devops_knowledge":
                return ToolExecutionResult(name, True, {"results": []})
            return ToolExecutionResult(
                name,
                False,
                error="credentials unavailable",
            )

    result = create_aiops_investigator(FailingRegistry())(["aws"])

    assert result["incidents"][0]["type"] == "provider_failure"
    assert result["proposals"][0]["requires_approval"] is True
