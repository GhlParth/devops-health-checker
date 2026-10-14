import pytest

from devops_health_checker.rag.chunker import DocumentChunk
from devops_health_checker.rag.documents import Document
from devops_health_checker.rag.vector_store import TfidfVectorStore


def test_vector_store_ranks_relevant_chunks_and_preserves_metadata() -> None:
    chunks = [
        DocumentChunk("Pod logs show a crash", "pods.md", "kubernetes", 0),
        DocumentChunk("EC2 instance health", "aws.md", "aws", 0),
        DocumentChunk("Pod events explain a restart", "pods.md", "kubernetes", 1),
    ]
    store = TfidfVectorStore(chunks)

    results = store.search("pod restart")

    assert results[0].chunk.source == "pods.md"
    assert results[0].chunk.chunk_index == 1
    assert results[0].score > 0
    assert results[0].matched_terms == ("pod", "restart")


def test_vector_store_can_be_built_from_documents() -> None:
    documents = [Document("Kubernetes pod logs", "pods.md", "kubernetes")]

    store = TfidfVectorStore.from_documents(documents)

    assert store.search("logs")[0].chunk.source == "pods.md"


def test_vector_store_returns_empty_for_unknown_terms() -> None:
    store = TfidfVectorStore([DocumentChunk("Kubernetes pod", "pods.md", "kubernetes", 0)])

    assert store.search("database") == []
    assert store.search("") == []


def test_vector_store_rejects_non_positive_top_k() -> None:
    with pytest.raises(ValueError):
        TfidfVectorStore().search("pod", top_k=0)
