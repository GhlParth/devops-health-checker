import json

from devops_health_checker.main import run_knowledge_search


class MockRegistry:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def run(self, name, **kwargs):
        self.calls.append((name, kwargs))
        if self.error:
            raise self.error
        return self.result


def test_run_knowledge_search_prints_json(capsys) -> None:
    registry = MockRegistry({"match_count": 1, "results": []})

    exit_code = run_knowledge_search(registry, "pod logs")

    assert exit_code == 0
    assert registry.calls == [
        ("search_devops_knowledge", {"query": "pod logs"})
    ]
    assert json.loads(capsys.readouterr().out)["match_count"] == 1


def test_run_knowledge_search_reports_tool_failure(capsys) -> None:
    registry = MockRegistry(error=RuntimeError("index unavailable"))

    exit_code = run_knowledge_search(registry, "pod logs")

    assert exit_code == 1
    assert "Knowledge search error: index unavailable" in capsys.readouterr().out
