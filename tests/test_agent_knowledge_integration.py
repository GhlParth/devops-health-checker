from devops_health_checker.agent import DevOpsAgent
from devops_health_checker.models import HealthResult, HealthStatus
from devops_health_checker.registry import ToolRegistry
from devops_health_checker.schemas import ToolParameter, ToolSchema


class MockLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, tools=None):
        self.calls.append(messages)
        return self.responses.pop(0)


def _tool_call_response(tool_calls):
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls,
                }
            }
        ]
    }


def test_agent_combines_live_health_and_knowledge_results() -> None:
    registry = ToolRegistry()
    registry.register(
        name="kubernetes_health",
        description="Check Kubernetes health.",
        function=lambda: HealthResult(
            name="kubernetes",
            status=HealthStatus.WARNING,
            details={"unhealthy_pods": 1},
            errors=[],
        ),
        schema=ToolSchema(
            name="kubernetes_health",
            description="Check Kubernetes health.",
        ),
    )
    registry.register(
        name="search_devops_knowledge",
        description="Search troubleshooting guidance.",
        function=lambda query: {
            "query": query,
            "results": [{"source": "kubernetes/pods.md"}],
        },
        schema=ToolSchema(
            name="search_devops_knowledge",
            description="Search troubleshooting guidance.",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Troubleshooting query.",
                    required=True,
                )
            ],
        ),
    )

    llm = MockLLM(
        [
            _tool_call_response(
                [
                    {
                        "type": "function",
                        "id": "health-call",
                        "function": {
                            "name": "kubernetes_health",
                            "arguments": "{}",
                        },
                    }
                ]
            ),
            _tool_call_response(
                [
                    {
                        "type": "function",
                        "id": "knowledge-call",
                        "function": {
                            "name": "search_devops_knowledge",
                            "arguments": '{"query":"unhealthy pod"}',
                        },
                    }
                ]
            ),
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "See kubernetes/pods.md for guidance.",
                        }
                    }
                ]
            },
        ]
    )

    answer = DevOpsAgent(registry, llm_client=llm).run("Diagnose my unhealthy Kubernetes pod.")

    assert answer == "See kubernetes/pods.md for guidance."
    assert len(llm.calls) == 3
    assert "kubernetes/pods.md" in llm.calls[2][-1]["content"]
