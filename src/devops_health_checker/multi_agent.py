from dataclasses import dataclass, field
from typing import Any

from devops_health_checker.agent import DevOpsAgent


SPECIALIST_KEYWORDS: dict[str, tuple[str, ...]] = {
    "kubernetes": (
        "kubernetes",
        "k8s",
        "pod",
        "deployment",
        "namespace",
        "container",
    ),
    "aws": (
        "aws",
        "ec2",
        "s3",
        "iam",
        "cloud",
    ),
    "security": (
        "security",
        "permission",
        "secret",
        "token",
        "vulnerability",
        "injection",
    ),
    "sre": (
        "incident",
        "outage",
        "reliability",
        "latency",
        "availability",
        "health",
    ),
}


SPECIALIST_PROMPTS = {
    "kubernetes": "Focus on Kubernetes and container evidence.",
    "aws": "Focus on AWS and cloud-resource evidence.",
    "security": "Focus on security, permissions, secrets, and safe boundaries.",
    "sre": "Focus on incident impact, reliability, and evidence-based triage.",
}


@dataclass
class MultiAgentResult:
    selected_specialists: list[str]
    responses: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_specialists": self.selected_specialists,
            "responses": dict(self.responses),
            "errors": dict(self.errors),
        }


class MultiAgentCoordinator:
    """Route a request to a small, explicit set of specialist agents."""

    def __init__(
        self,
        registry,
        llm_client=None,
        max_specialists: int = 2,
    ):
        if max_specialists <= 0:
            raise ValueError("max_specialists must be greater than zero")
        self.registry = registry
        self.llm_client = llm_client
        self.max_specialists = max_specialists

    def select_specialists(self, message: str) -> list[str]:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must not be empty")

        normalized_message = message.lower()
        scores = {
            specialist: sum(
                keyword in normalized_message
                for keyword in keywords
            )
            for specialist, keywords in SPECIALIST_KEYWORDS.items()
        }
        selected = [
            specialist
            for specialist, score in sorted(
                scores.items(),
                key=lambda item: (-item[1], item[0]),
            )
            if score > 0
        ]

        if not selected:
            selected = ["sre"]
        return selected[: self.max_specialists]

    def run(self, message: str) -> MultiAgentResult:
        selected = self.select_specialists(message)
        result = MultiAgentResult(selected_specialists=selected)

        for specialist in selected:
            prompt = (
                f"You are the {specialist} specialist. "
                f"{SPECIALIST_PROMPTS[specialist]} "
                "Provide evidence-based guidance and identify uncertainty.\n\n"
                f"User request: {message}"
            )
            try:
                response = DevOpsAgent(
                    registry=self.registry,
                    llm_client=self.llm_client,
                ).run(prompt)
            except Exception as error:
                result.errors[specialist] = str(error)
            else:
                result.responses[specialist] = response

        return result
