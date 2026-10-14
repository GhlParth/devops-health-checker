import pytest

from devops_health_checker.models import HealthResult, HealthStatus
from devops_health_checker.registry import ToolRegistry
from devops_health_checker.schemas import ToolSchema
from devops_health_checker.workflow import DevOpsWorkflow


class MockLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    def chat(self, messages, tools=None):
        return self.responses.pop(0)


def tool_call_response():
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "type": "function",
                    "id": "workflow-call",
                    "function": {
                        "name": "health",
                        "arguments": "{}",
                    },
                }],
            }
        }]
    }


def final_response():
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "Workflow completed.",
            }
        }]
    }


def create_registry():
    registry = ToolRegistry()
    registry.register(
        name="health",
        description="Read health.",
        function=lambda: HealthResult(
            name="test",
            status=HealthStatus.HEALTHY,
        ),
        schema=ToolSchema(name="health", description="Read health."),
    )
    return registry


def test_workflow_records_routes_and_tool_results() -> None:
    workflow = DevOpsWorkflow(
        create_registry(),
        llm_client=MockLLM([tool_call_response(), final_response()]),
    )

    assert workflow.run("Check health") == "Workflow completed."
    assert workflow.last_state.status == "completed"
    assert workflow.last_state.route == "end"
    assert workflow.last_state.iteration == 2
    assert workflow.last_state.tool_results[0]["success"] is True


def test_workflow_rejects_empty_messages() -> None:
    workflow = DevOpsWorkflow(create_registry(), llm_client=MockLLM([]))

    with pytest.raises(ValueError, match="user_message"):
        workflow.run(" ")


def test_workflow_records_failure_on_iteration_limit() -> None:
    workflow = DevOpsWorkflow(
        create_registry(),
        llm_client=MockLLM([tool_call_response()]),
        max_iterations=1,
    )

    with pytest.raises(RuntimeError, match="maximum number"):
        workflow.run("Keep checking")

    assert workflow.last_state.status == "failed"
    assert workflow.last_state.route == "error"
    assert workflow.last_state.iteration == 1


def test_workflow_rejects_non_positive_iteration_limit() -> None:
    with pytest.raises(ValueError, match="max_iterations"):
        DevOpsWorkflow(create_registry(), max_iterations=0)
