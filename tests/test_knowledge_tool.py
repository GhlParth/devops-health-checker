import pytest

from devops_health_checker.tools import knowledge
from devops_health_checker.tools.knowledge import (
    search_devops_knowledge,
)
from devops_health_checker.tools.registry import (
    create_tool_registry,
)


def test_search_devops_knowledge_returns_source_metadata() -> None:
    result = search_devops_knowledge("pod crash loop")

    assert result["query"] == "pod crash loop"
    assert result["match_count"] > 0
    assert result["results"][0]["source"] == ("kubernetes/pod-troubleshooting.md")
    assert result["results"][0]["category"] == "kubernetes"


def test_search_devops_knowledge_rejects_blank_query() -> None:
    with pytest.raises(ValueError, match="query must not be empty"):
        search_devops_knowledge("   ")


def test_search_devops_knowledge_returns_no_matches_when_directory_is_missing(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(knowledge, "KNOWLEDGE_DIR", tmp_path / "missing")

    result = search_devops_knowledge("pod logs")

    assert result["match_count"] == 0
    assert result["results"] == []


def test_knowledge_tool_is_registered_with_validation() -> None:
    registry = create_tool_registry()

    result = registry.execute(
        "search_devops_knowledge",
        {"query": "pod logs", "top_k": 1},
    )

    assert result.success is True
    assert result.result["match_count"] == 1


def test_knowledge_tool_rejects_unknown_arguments() -> None:
    registry = create_tool_registry()

    result = registry.execute(
        "search_devops_knowledge",
        {"query": "pod", "path": "/tmp"},
    )

    assert result.success is False
    assert "Unknown parameter" in result.error


def test_knowledge_tool_rejects_malformed_arguments() -> None:
    registry = create_tool_registry()

    result = registry.execute(
        "search_devops_knowledge",
        {"query": "pod", "top_k": "one"},
    )

    assert result.success is False
    assert "must be of type integer" in result.error


def test_knowledge_index_is_reused_and_invalidated_when_files_change(
    tmp_path,
    monkeypatch,
) -> None:
    document_path = tmp_path / "runbook.md"
    document_path.write_text("pod logs", encoding="utf-8")
    monkeypatch.setattr(knowledge, "KNOWLEDGE_DIR", tmp_path)
    monkeypatch.setattr(knowledge, "_cached_store", None)
    monkeypatch.setattr(knowledge, "_cached_signature", None)

    first_store = knowledge._get_store()
    second_store = knowledge._get_store()
    document_path.write_text("pod events", encoding="utf-8")
    third_store = knowledge._get_store()

    assert first_store is second_store
    assert third_store is not first_store
