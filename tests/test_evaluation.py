from devops_health_checker.rag.evaluation import (
    AgentEvaluationCase,
    evaluate_agent,
)


class MockAgent:
    def run(self, prompt):
        return "Kubernetes is warning. See kubernetes/pods.md."


def test_evaluate_agent_reports_pass_rate() -> None:
    metrics = evaluate_agent(
        MockAgent(),
        [
            AgentEvaluationCase(
                "Diagnose pod",
                expected_phrases=("warning",),
                expected_sources=("kubernetes/pods.md",),
            ),
            AgentEvaluationCase(
                "Diagnose database",
                expected_phrases=("critical",),
            ),
        ],
    )

    assert metrics["cases"] == 2
    assert metrics["passed"] == 1
    assert metrics["pass_rate"] == 0.5
