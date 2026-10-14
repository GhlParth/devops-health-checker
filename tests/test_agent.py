import json

from devops_health_checker.agent import DevOpsAgent
from devops_health_checker.models import (
    HealthResult,
    HealthStatus,
)
from devops_health_checker.registry import ToolRegistry
from devops_health_checker.schemas import (
    ToolSchema,
)


class MockLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, tools=None):
        self.calls.append(
            {
                "messages": messages,
                "tools": tools,
            }
        )

        if not self.responses:
            raise AssertionError("MockLLM has no remaining responses.")

        return self.responses.pop(0)


def create_mock_registry():
    registry = ToolRegistry()

    def mock_kubernetes_health(
        namespace=None,
    ):
        return HealthResult(
            name="kubernetes",
            status=HealthStatus.HEALTHY,
            details={
                "namespace": namespace,
                "total_nodes": 1,
                "unhealthy_nodes": 0,
                "total_pods": 2,
                "unhealthy_pods": 0,
            },
            errors=[],
        )

    registry.register(
        name="kubernetes_health",
        description=("Check Kubernetes health."),
        function=mock_kubernetes_health,
        schema=ToolSchema(
            name="kubernetes_health",
            description=("Check Kubernetes health."),
        ),
    )

    return registry


def test_agent_executes_tool_and_returns_final_answer():
    registry = create_mock_registry()

    tool_call_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "type": "function",
                            "id": "call-123",
                            "function": {
                                "name": ("kubernetes_health"),
                                "arguments": "{}",
                            },
                        }
                    ],
                }
            }
        ]
    }

    final_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": ("The Kubernetes cluster is healthy."),
                }
            }
        ]
    }

    llm = MockLLM(
        [
            tool_call_response,
            final_response,
        ]
    )

    agent = DevOpsAgent(
        registry=registry,
        llm_client=llm,
    )

    answer = agent.run("Check Kubernetes health.")

    assert answer == ("The Kubernetes cluster is healthy.")

    assert len(llm.calls) == 2


def test_agent_sends_tool_result_back_to_llm():
    registry = create_mock_registry()

    tool_call_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "type": "function",
                            "id": "call-456",
                            "function": {
                                "name": ("kubernetes_health"),
                                "arguments": "{}",
                            },
                        }
                    ],
                }
            }
        ]
    }

    final_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Cluster is healthy.",
                }
            }
        ]
    }

    llm = MockLLM(
        [
            tool_call_response,
            final_response,
        ]
    )

    agent = DevOpsAgent(
        registry=registry,
        llm_client=llm,
    )

    agent.run("Check Kubernetes.")

    second_call = llm.calls[1]

    tool_messages = [message for message in second_call["messages"] if message["role"] == "tool"]

    assert len(tool_messages) == 1

    tool_message = tool_messages[0]

    assert tool_message["tool_call_id"] == ("call-456")

    result = json.loads(tool_message["content"])

    assert result["success"] is True
    assert result["result"]["name"] == ("kubernetes")
    assert result["result"]["status"] == ("HEALTHY")


def test_agent_handles_invalid_tool_arguments():
    registry = create_mock_registry()

    tool_call_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "type": "function",
                            "id": "call-invalid",
                            "function": {
                                "name": ("kubernetes_health"),
                                "arguments": ('{"unknown": "value"}'),
                            },
                        }
                    ],
                }
            }
        ]
    }

    final_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": ("The requested check could not be executed."),
                }
            }
        ]
    }

    llm = MockLLM(
        [
            tool_call_response,
            final_response,
        ]
    )

    agent = DevOpsAgent(
        registry=registry,
        llm_client=llm,
    )

    answer = agent.run("Check Kubernetes.")

    assert answer == ("The requested check could not be executed.")

    second_call = llm.calls[1]

    tool_messages = [message for message in second_call["messages"] if message["role"] == "tool"]

    assert len(tool_messages) == 1

    result = json.loads(tool_messages[0]["content"])

    assert result["success"] is False
    assert "Unknown parameter" in result["error"]


def test_agent_handles_invalid_json_arguments():
    registry = create_mock_registry()

    tool_call_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "type": "function",
                            "id": "call-json",
                            "function": {
                                "name": ("kubernetes_health"),
                                "arguments": ('{"namespace":'),
                            },
                        }
                    ],
                }
            }
        ]
    }

    final_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": ("The tool request was invalid."),
                }
            }
        ]
    }

    llm = MockLLM(
        [
            tool_call_response,
            final_response,
        ]
    )

    agent = DevOpsAgent(
        registry=registry,
        llm_client=llm,
    )

    answer = agent.run("Check Kubernetes.")

    assert answer == ("The tool request was invalid.")

    second_call = llm.calls[1]

    tool_messages = [message for message in second_call["messages"] if message["role"] == "tool"]

    result = json.loads(tool_messages[0]["content"])

    assert result["success"] is False
    assert "Invalid JSON arguments" in (result["error"])


def test_agent_returns_direct_llm_answer():
    registry = create_mock_registry()

    response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": ("I can help with DevOps health checks."),
                }
            }
        ]
    }

    llm = MockLLM([response])

    agent = DevOpsAgent(
        registry=registry,
        llm_client=llm,
    )

    answer = agent.run("What can you do?")

    assert answer == ("I can help with DevOps health checks.")

    assert len(llm.calls) == 1


def test_agent_rejects_llm_error_response():
    registry = create_mock_registry()

    response = {
        "error": {
            "message": "Temporary LLM failure",
        }
    }

    llm = MockLLM([response])

    agent = DevOpsAgent(
        registry=registry,
        llm_client=llm,
    )

    try:
        agent.run("Check Kubernetes.")
        assert False, "Expected RuntimeError"

    except RuntimeError as error:
        assert "LLM returned an error" in (str(error))


def test_agent_enforces_max_iterations():
    registry = create_mock_registry()

    tool_call_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "type": "function",
                            "id": "call-loop",
                            "function": {
                                "name": ("kubernetes_health"),
                                "arguments": "{}",
                            },
                        }
                    ],
                }
            }
        ]
    }

    llm = MockLLM(
        [
            tool_call_response,
            tool_call_response,
            tool_call_response,
        ]
    )

    agent = DevOpsAgent(
        registry=registry,
        llm_client=llm,
        max_iterations=2,
    )

    try:
        agent.run("Keep checking Kubernetes.")
        assert False, "Expected maximum iteration error"

    except RuntimeError as error:
        assert "maximum number" in (str(error)).lower()

    assert len(llm.calls) == 2
