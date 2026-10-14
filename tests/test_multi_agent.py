import pytest

from devops_health_checker.multi_agent import MultiAgentCoordinator
from devops_health_checker.registry import ToolRegistry


class MockLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    def chat(self, messages, tools=None):
        return self.responses.pop(0)


def final_response(text):
    return {
        "choices": [{
            "message": {"role": "assistant", "content": text}
        }]
    }


def test_router_selects_relevant_specialists_and_caps_count():
    coordinator = MultiAgentCoordinator(
        ToolRegistry(),
        max_specialists=2,
    )

    selected = coordinator.select_specialists(
        "Kubernetes pod security incident in AWS"
    )

    assert len(selected) == 2
    assert "kubernetes" in selected
    assert "aws" in selected


def test_router_uses_sre_fallback():
    coordinator = MultiAgentCoordinator(ToolRegistry())

    assert coordinator.select_specialists("What should we investigate?") == [
        "sre"
    ]


def test_multi_agent_aggregates_specialist_responses():
    coordinator = MultiAgentCoordinator(
        ToolRegistry(),
        llm_client=MockLLM([
            final_response("Kubernetes evidence."),
            final_response("AWS evidence."),
        ]),
        max_specialists=2,
    )

    result = coordinator.run("Kubernetes pod in AWS")

    assert result.selected_specialists == ["kubernetes", "aws"]
    assert result.responses == {
        "kubernetes": "Kubernetes evidence.",
        "aws": "AWS evidence.",
    }
    assert result.errors == {}


def test_multi_agent_isolates_specialist_failure():
    class FailingLLM:
        def chat(self, messages, tools=None):
            raise RuntimeError("provider unavailable")

    result = MultiAgentCoordinator(
        ToolRegistry(),
        llm_client=FailingLLM(),
    ).run("Kubernetes pod")

    assert result.errors
    assert not result.responses


def test_multi_agent_rejects_invalid_limits():
    with pytest.raises(ValueError):
        MultiAgentCoordinator(ToolRegistry(), max_specialists=0)
