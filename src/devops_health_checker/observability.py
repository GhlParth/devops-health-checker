from dataclasses import dataclass, field
from typing import Any

from prometheus_client import Counter, Histogram

# ─── Prometheus metrics (module-level singletons) ────────────────────────────

_NAMESPACE = "devops_health_checker"

tool_calls_total = Counter(
    f"{_NAMESPACE}_tool_calls_total",
    "Total number of tool executions",
    ["tool_name", "status"],
)

tool_duration_seconds = Histogram(
    f"{_NAMESPACE}_tool_duration_seconds",
    "Tool execution duration in seconds",
    ["tool_name"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

llm_calls_total = Counter(
    f"{_NAMESPACE}_llm_calls_total",
    "Total number of LLM API calls",
    ["model", "status"],
)

llm_duration_seconds = Histogram(
    f"{_NAMESPACE}_llm_duration_seconds",
    "LLM API call duration in seconds",
    ["model"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

llm_tokens_total = Counter(
    f"{_NAMESPACE}_llm_tokens_total",
    "Total LLM tokens consumed",
    ["model", "token_type"],
)

llm_cost_usd_total = Counter(
    f"{_NAMESPACE}_llm_cost_usd_total",
    "Estimated total LLM cost in USD",
    ["model"],
)


# ─── In-process summary (unchanged public interface) ─────────────────────────


@dataclass
class MetricsCollector:
    """In-process metrics snapshot.

    Dual-writes to Prometheus counters/histograms (exported via /metrics) and
    to its own counters for backward-compatible snapshot().
    """

    tool_calls: dict[str, int] = field(default_factory=dict)
    tool_failures: dict[str, int] = field(default_factory=dict)
    tool_duration_ms: dict[str, float] = field(default_factory=dict)
    llm_calls: int = 0
    llm_failures: int = 0
    llm_duration_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    _model: str = field(default="unknown", repr=False)

    def record_tool(self, execution: Any) -> None:
        name = execution.tool_name
        status = "success" if execution.success else "failure"
        duration_s = execution.duration_ms / 1000

        # Prometheus
        tool_calls_total.labels(tool_name=name, status=status).inc()
        tool_duration_seconds.labels(tool_name=name).observe(duration_s)

        # In-process summary
        self.tool_calls[name] = self.tool_calls.get(name, 0) + 1
        self.tool_duration_ms[name] = self.tool_duration_ms.get(name, 0.0) + execution.duration_ms
        if not execution.success:
            self.tool_failures[name] = self.tool_failures.get(name, 0) + 1

    def record_llm(self, response: dict[str, Any], duration_ms: float) -> None:
        status = "error" if "error" in response else "success"
        model = self._model or "unknown"
        duration_s = duration_ms / 1000

        # Prometheus
        llm_calls_total.labels(model=model, status=status).inc()
        llm_duration_seconds.labels(model=model).observe(duration_s)

        usage = response.get("usage") or {}
        prompt = int(usage.get("prompt_tokens", 0) or 0)
        completion = int(usage.get("completion_tokens", 0) or 0)
        cost = float(usage.get("cost", 0.0) or 0.0)

        if prompt:
            llm_tokens_total.labels(model=model, token_type="prompt").inc(prompt)
        if completion:
            llm_tokens_total.labels(model=model, token_type="completion").inc(completion)
        if cost:
            llm_cost_usd_total.labels(model=model).inc(cost)

        # In-process summary
        self.llm_calls += 1
        self.llm_duration_ms += duration_ms
        if "error" in response:
            self.llm_failures += 1
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.estimated_cost_usd += cost

    def snapshot(self) -> dict[str, Any]:
        return {
            "tools": {
                "calls": dict(self.tool_calls),
                "failures": dict(self.tool_failures),
                "duration_ms": {
                    name: round(duration, 2) for name, duration in self.tool_duration_ms.items()
                },
            },
            "llm": {
                "calls": self.llm_calls,
                "failures": self.llm_failures,
                "duration_ms": round(self.llm_duration_ms, 2),
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
                "estimated_cost_usd": round(self.estimated_cost_usd, 8),
            },
        }
