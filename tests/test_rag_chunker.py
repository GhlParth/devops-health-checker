import pytest

from devops_health_checker.rag.chunker import (
    DocumentChunk,
    chunk_document,
    chunk_documents,
)
from devops_health_checker.rag.documents import Document


def test_chunk_document_preserves_metadata_and_overlap() -> None:
    document = Document(
        content="abcdefghij",
        source="kubernetes/pods.md",
        category="kubernetes",
    )

    chunks = chunk_document(document, chunk_size=6, overlap=2)

    assert chunks == [
        DocumentChunk("abcdef", "kubernetes/pods.md", "kubernetes", 0),
        DocumentChunk("efghij", "kubernetes/pods.md", "kubernetes", 1),
    ]


def test_chunk_documents_preserves_document_order() -> None:
    documents = [
        Document("12345", "one.md", "general"),
        Document("abc", "two.md", "general"),
    ]

    chunks = chunk_documents(documents, chunk_size=3, overlap=0)

    assert [(chunk.source, chunk.content) for chunk in chunks] == [
        ("one.md", "123"),
        ("one.md", "45"),
        ("two.md", "abc"),
    ]


def test_empty_document_produces_no_chunks() -> None:
    document = Document("", "empty.md", "general")

    assert chunk_document(document) == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)],
)
def test_invalid_chunk_options_raise_value_error(
    chunk_size: int,
    overlap: int,
) -> None:
    document = Document("content", "document.md", "general")

    with pytest.raises(ValueError):
        chunk_document(document, chunk_size, overlap)
