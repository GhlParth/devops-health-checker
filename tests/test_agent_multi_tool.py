from devops_health_checker.agent import DevOpsAgent
from devops_health_checker.execution import (
    ToolExecutionResult,
)


class MockLLM:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def chat(self, messages, tools=None):
        self.calls.append(
            {
                "messages": messages,
                "tools": tools,
            }
        )

        if not self.responses:
            raise AssertionError("MockLLM has no more responses.")

        return self.responses.pop(0)


class MockRegistry:
    def __init__(self):
        self.executed = []

    def list_tools(self):
        return []

    def execute(
        self,
        name,
        arguments=None,
    ):
        self.executed.append(
            {
                "name": name,
                "arguments": arguments,
            }
        )

        results = {
            "kubernetes_health": {
                "status": "HEALTHY",
                "nodes": 1,
                "unhealthy_nodes": 0,
                "pods": 9,
                "unhealthy_pods": 0,
            },
            "github_repository": {
                "repository": "kubernetes/kubernetes",
                "stars": 120000,
                "open_issues": 1000,
            },
            "aws_ec2_health": {
                "total_instances": 3,
                "running_instances": 3,
                "stopped_instances": 0,
            },
        }

        result = results.get(name)

        if result is None:
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                result=None,
                error=f"Unknown tool: {name}",
            )

        return ToolExecutionResult(
            tool_name=name,
            success=True,
            result=result,
            error=None,
        )


class PartialFailureRegistry(MockRegistry):
    def execute(
        self,
        name,
        arguments=None,
    ):
        self.executed.append(
            {
                "name": name,
                "arguments": arguments,
            }
        )

        if name == "aws_ec2_health":
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                result=None,
                error="AWS credentials are invalid.",
            )

        return ToolExecutionResult(
            tool_name=name,
            success=True,
            result={
                "status": "HEALTHY",
            },
            error=None,
        )


def make_tool_call(
    tool_call_id,
    tool_name,
    arguments="{}",
):
    return {
        "id": tool_call_id,
        "type": "function",
        "function": {
            "name": tool_name,
            "arguments": arguments,
        },
    }


def test_agent_executes_multiple_tools():
    registry = MockRegistry()

    llm = MockLLM(
        [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                make_tool_call(
                                    "call-k8s",
                                    "kubernetes_health",
                                ),
                                make_tool_call(
                                    "call-github",
                                    "github_repository",
                                    ('{"owner":"kubernetes","repository":"kubernetes"}'),
                                ),
                            ],
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": (
                                "Kubernetes is healthy and the GitHub repository is available."
                            ),
                        }
                    }
                ]
            },
        ]
    )

    agent = DevOpsAgent(
        registry=registry,
        llm_client=llm,
    )

    answer = agent.run("Check Kubernetes and GitHub.")

    assert answer == "Kubernetes is healthy and the GitHub repository is available."

    assert len(registry.executed) == 2

    assert registry.executed[0]["name"] == ("kubernetes_health")

    assert registry.executed[1]["name"] == ("github_repository")

    assert registry.executed[1]["arguments"] == {
        "owner": "kubernetes",
        "repository": "kubernetes",
    }


def test_agent_executes_three_tools():
    registry = MockRegistry()

    llm = MockLLM(
        [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                make_tool_call(
                                    "call-k8s",
                                    "kubernetes_health",
                                ),
                                make_tool_call(
                                    "call-github",
                                    "github_repository",
                                    ('{"owner":"kubernetes","repository":"kubernetes"}'),
                                ),
                                make_tool_call(
                                    "call-aws",
                                    "aws_ec2_health",
                                ),
                            ],
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": ("Kubernetes, GitHub, and AWS checks completed."),
                        }
                    }
                ]
            },
        ]
    )

    agent = DevOpsAgent(
        registry=registry,
        llm_client=llm,
    )

    answer = agent.run("Check Kubernetes, GitHub, and AWS.")

    assert answer == ("Kubernetes, GitHub, and AWS checks completed.")

    assert len(registry.executed) == 3

    executed_tools = [item["name"] for item in registry.executed]

    assert executed_tools == [
        "kubernetes_health",
        "github_repository",
        "aws_ec2_health",
    ]


def test_agent_sends_all_tool_results_back_to_llm():
    registry = MockRegistry()

    llm = MockLLM(
        [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                make_tool_call(
                                    "call-k8s",
                                    "kubernetes_health",
                                ),
                                make_tool_call(
                                    "call-github",
                                    "github_repository",
                                    ('{"owner":"kubernetes","repository":"kubernetes"}'),
                                ),
                            ],
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": ("Both infrastructure and repository checks completed."),
                        }
                    }
                ]
            },
        ]
    )

    agent = DevOpsAgent(
        registry=registry,
        llm_client=llm,
    )

    agent.run("Check Kubernetes and GitHub.")

    assert len(llm.calls) == 2

    second_messages = llm.calls[1]["messages"]

    tool_messages = [message for message in second_messages if message.get("role") == "tool"]

    assert len(tool_messages) == 2

    tool_call_ids = [message["tool_call_id"] for message in tool_messages]

    assert tool_call_ids == [
        "call-k8s",
        "call-github",
    ]

    assert "kubernetes_health" in (tool_messages[0]["content"])

    assert "github_repository" in (tool_messages[1]["content"])


def test_agent_handles_one_failed_tool():
    registry = PartialFailureRegistry()

    llm = MockLLM(
        [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                make_tool_call(
                                    "call-k8s",
                                    "kubernetes_health",
                                ),
                                make_tool_call(
                                    "call-aws",
                                    "aws_ec2_health",
                                ),
                            ],
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": (
                                "Kubernetes is healthy, "
                                "but AWS could not be checked "
                                "because credentials are invalid."
                            ),
                        }
                    }
                ]
            },
        ]
    )

    agent = DevOpsAgent(
        registry=registry,
        llm_client=llm,
    )

    answer = agent.run("Check Kubernetes and AWS.")

    assert answer == (
        "Kubernetes is healthy, but AWS could not be checked because credentials are invalid."
    )

    assert len(registry.executed) == 2

    second_messages = llm.calls[1]["messages"]

    tool_messages = [message for message in second_messages if message.get("role") == "tool"]

    assert len(tool_messages) == 2

    assert "AWS credentials are invalid." in (tool_messages[1]["content"])
