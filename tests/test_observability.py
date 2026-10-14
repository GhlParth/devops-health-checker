from devops_health_checker.execution import ToolExecutionResult
from devops_health_checker.observability import MetricsCollector


def test_metrics_collect_tool_and_llm_usage() -> None:
    metrics = MetricsCollector()
    metrics.record_tool(ToolExecutionResult("health", True, duration_ms=12.5))
    metrics.record_tool(ToolExecutionResult("health", False, error="failed", duration_ms=2.5))
    metrics.record_llm(
        {
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "cost": 0.001,
            }
        },
        20.0,
    )

    snapshot = metrics.snapshot()

    assert snapshot["tools"]["calls"] == {"health": 2}
    assert snapshot["tools"]["failures"] == {"health": 1}
    assert snapshot["tools"]["duration_ms"] == {"health": 15.0}
    assert snapshot["llm"]["total_tokens"] == 15
    assert snapshot["llm"]["estimated_cost_usd"] == 0.001
