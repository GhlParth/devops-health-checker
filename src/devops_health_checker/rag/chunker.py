from dataclasses import dataclass

from devops_health_checker.rag.documents import Document


@dataclass(frozen=True)
class DocumentChunk:
    content: str
    source: str
    category: str
    chunk_index: int


def chunk_document(
    document: Document,
    chunk_size: int = 1000,
    overlap: int = 100,
) -> list[DocumentChunk]:
    """Split one document into deterministic, overlapping character chunks."""
    _validate_chunk_options(chunk_size, overlap)

    if not document.content:
        return []

    step = chunk_size - overlap
    chunks: list[DocumentChunk] = []

    for chunk_index, start in enumerate(range(0, len(document.content), step)):
        content = document.content[start : start + chunk_size]
        chunks.append(
            DocumentChunk(
                content=content,
                source=document.source,
                category=document.category,
                chunk_index=chunk_index,
            )
        )

        if start + chunk_size >= len(document.content):
            break

    return chunks


def chunk_documents(
    documents: list[Document],
    chunk_size: int = 1000,
    overlap: int = 100,
) -> list[DocumentChunk]:
    """Chunk documents in input order while preserving document metadata."""
    _validate_chunk_options(chunk_size, overlap)

    chunks: list[DocumentChunk] = []
    for document in documents:
        chunks.extend(chunk_document(document, chunk_size, overlap))
    return chunks


def _validate_chunk_options(chunk_size: int, overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0:
        raise ValueError("overlap must not be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
