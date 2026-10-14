import pytest

from devops_health_checker.rag.chunker import DocumentChunk
from devops_health_checker.rag.evaluation import (
    RetrievalCase,
    evaluate_retrieval,
)
from devops_health_checker.rag.search import SearchResult


def test_evaluate_retrieval_reports_metrics() -> None:
    chunks = [
        DocumentChunk("pod logs", "pods.md", "kubernetes", 0),
        DocumentChunk("instance state", "aws.md", "aws", 0),
    ]

    def search(query: str, top_k: int) -> list[SearchResult]:
        if query == "pod":
            return [SearchResult(chunks[0], 1.0, ("pod",))][:top_k]
        return [SearchResult(chunks[1], 1.0, ("instance",))][:top_k]

    metrics = evaluate_retrieval(
        search,
        [
            RetrievalCase("pod", ("pods.md",)),
            RetrievalCase("instance", ("aws.md",)),
        ],
        top_k=1,
    )

    assert metrics == {
        "queries": 2,
        "precision_at_k": 1.0,
        "recall": 1.0,
        "hit_rate": 1.0,
    }


def test_evaluate_retrieval_handles_empty_cases() -> None:
    assert evaluate_retrieval(lambda query, top_k: [], []) == {
        "queries": 0,
        "precision_at_k": 0.0,
        "recall": 0.0,
        "hit_rate": 0.0,
    }


def test_evaluate_retrieval_rejects_invalid_top_k() -> None:
    with pytest.raises(ValueError):
        evaluate_retrieval(lambda query, top_k: [], [], top_k=0)
