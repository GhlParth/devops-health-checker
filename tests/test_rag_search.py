import pytest

from devops_health_checker.rag.chunker import DocumentChunk
from devops_health_checker.rag.documents import Document
from devops_health_checker.rag.search import (
    SearchResult,
    search_chunks,
    search_documents,
)


def test_search_chunks_ranks_matches_and_returns_metadata() -> None:
    chunks = [
        DocumentChunk("Pod restart troubleshooting", "pods.md", "kubernetes", 0),
        DocumentChunk("Check pod logs and pod events", "pods.md", "kubernetes", 1),
        DocumentChunk("EC2 instance status", "aws.md", "aws", 0),
    ]

    results = search_chunks("pod logs", chunks)

    assert results == [
        SearchResult(chunks[1], 3, ("pod", "logs")),
        SearchResult(chunks[0], 1, ("pod",)),
    ]


def test_search_documents_chunks_before_searching() -> None:
    documents = [Document("Kubernetes pod logs are useful", "pods.md", "kubernetes")]

    results = search_documents("pod logs", documents, chunk_size=100, overlap=0)

    assert results
    assert results[0].chunk.source == "pods.md"
    assert results[0].matched_terms == ("pod", "logs")


def test_search_returns_empty_for_blank_or_unmatched_query() -> None:
    chunks = [DocumentChunk("Kubernetes pod", "pods.md", "kubernetes", 0)]

    assert search_chunks("", chunks) == []
    assert search_chunks("database", chunks) == []


def test_search_normalizes_kubernetes_status_terms() -> None:
    chunks = [
        DocumentChunk(
            "The container entered CrashLoopBackOff.",
            "pods.md",
            "kubernetes",
            0,
        )
    ]

    results = search_chunks("crash loop", chunks)

    assert results[0].chunk.source == "pods.md"


def test_search_rejects_non_positive_top_k() -> None:
    with pytest.raises(ValueError):
        search_chunks("pod", [], top_k=0)
