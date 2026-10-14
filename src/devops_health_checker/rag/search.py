from dataclasses import dataclass

from devops_health_checker.rag.chunker import DocumentChunk, chunk_documents
from devops_health_checker.rag.documents import Document
from devops_health_checker.rag.text import tokenize


@dataclass(frozen=True)
class SearchResult:
    chunk: DocumentChunk
    score: float
    matched_terms: tuple[str, ...]


def search_chunks(
    query: str,
    chunks: list[DocumentChunk],
    top_k: int = 5,
) -> list[SearchResult]:
    """Return deterministic keyword matches ranked by term frequency."""
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    query_terms = tokenize(query)
    if not query_terms:
        return []

    results: list[SearchResult] = []
    for chunk in chunks:
        content_terms = tokenize(chunk.content)
        term_counts = {term: content_terms.count(term) for term in query_terms}
        matched_terms = tuple(term for term in query_terms if term_counts[term] > 0)

        if not matched_terms:
            continue

        results.append(
            SearchResult(
                chunk=chunk,
                score=sum(term_counts[term] for term in matched_terms),
                matched_terms=matched_terms,
            )
        )

    results.sort(
        key=lambda result: (
            -result.score,
            result.chunk.source,
            result.chunk.chunk_index,
        )
    )
    return results[:top_k]


def search_documents(
    query: str,
    documents: list[Document],
    top_k: int = 5,
    chunk_size: int = 1000,
    overlap: int = 100,
) -> list[SearchResult]:
    """Chunk documents and search them without external embedding services."""
    chunks = chunk_documents(documents, chunk_size, overlap)
    return search_chunks(query, chunks, top_k)
