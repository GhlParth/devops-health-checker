from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricsCollector:
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

    def record_tool(self, execution) -> None:
        name = execution.tool_name
        self.tool_calls[name] = self.tool_calls.get(name, 0) + 1
        self.tool_duration_ms[name] = (
            self.tool_duration_ms.get(name, 0.0) + execution.duration_ms
        )
        if not execution.success:
            self.tool_failures[name] = self.tool_failures.get(name, 0) + 1

    def record_llm(self, response: dict[str, Any], duration_ms: float) -> None:
        self.llm_calls += 1
        self.llm_duration_ms += duration_ms
        if "error" in response:
            self.llm_failures += 1

        usage = response.get("usage") or {}
        self.prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
        self.completion_tokens += int(usage.get("completion_tokens", 0) or 0)
        self.total_tokens += int(usage.get("total_tokens", 0) or 0)
        self.estimated_cost_usd += float(usage.get("cost", 0.0) or 0.0)

    def snapshot(self) -> dict[str, Any]:
        return {
            "tools": {
                "calls": dict(self.tool_calls),
                "failures": dict(self.tool_failures),
                "duration_ms": {
                    name: round(duration, 2)
                    for name, duration in self.tool_duration_ms.items()
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
