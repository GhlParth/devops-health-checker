import math
from collections import Counter
from collections.abc import Iterable

from devops_health_checker.rag.chunker import DocumentChunk, chunk_documents
from devops_health_checker.rag.documents import Document
from devops_health_checker.rag.search import SearchResult
from devops_health_checker.rag.text import tokenize


class TfidfVectorStore:
    """Small in-memory TF-IDF index with cosine-similarity search.

    TF-IDF is a local, dependency-free baseline. It is vector retrieval, but
    it is not a semantic embedding model and should be replaced or augmented
    when a suitable local embedding dependency is selected.
    """

    def __init__(self, chunks: Iterable[DocumentChunk] = ()) -> None:
        self._chunks = list(chunks)
        self._vectors: list[dict[str, float]] = []
        self._idf: dict[str, float] = {}
        self._rebuild()

    @classmethod
    def from_documents(
        cls,
        documents: list[Document],
        chunk_size: int = 1000,
        overlap: int = 100,
    ) -> "TfidfVectorStore":
        return cls(chunk_documents(documents, chunk_size, overlap))

    def add_chunks(self, chunks: Iterable[DocumentChunk]) -> None:
        self._chunks.extend(chunks)
        self._rebuild()

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        query_terms = tokenize(query)
        if not query_terms or not self._chunks:
            return []

        query_vector = self._weighted_vector(Counter(query_terms))
        query_norm = _vector_norm(query_vector)
        if query_norm == 0:
            return []

        results: list[SearchResult] = []
        for chunk, vector in zip(self._chunks, self._vectors):
            score = _dot_product(query_vector, vector) / (query_norm * _vector_norm(vector))
            if score == 0:
                continue

            matched_terms = tuple(term for term in query_terms if term in vector)
            results.append(SearchResult(chunk, score, matched_terms))

        results.sort(
            key=lambda result: (
                -result.score,
                result.chunk.source,
                result.chunk.chunk_index,
            )
        )
        return results[:top_k]

    def _rebuild(self) -> None:
        document_terms = [tokenize(chunk.content) for chunk in self._chunks]
        document_count = len(document_terms)
        document_frequency: Counter[str] = Counter()

        for terms in document_terms:
            document_frequency.update(set(terms))

        self._idf = {
            term: math.log((1 + document_count) / (1 + frequency)) + 1
            for term, frequency in document_frequency.items()
        }
        self._vectors = [self._weighted_vector(Counter(terms)) for terms in document_terms]

    def _weighted_vector(self, term_counts: Counter[str]) -> dict[str, float]:
        return {
            term: (1 + math.log(count)) * self._idf[term]
            for term, count in term_counts.items()
            if term in self._idf
        }


def _vector_norm(vector: dict[str, float]) -> float:
    return math.sqrt(sum(value * value for value in vector.values()))


def _dot_product(
    left: dict[str, float],
    right: dict[str, float],
) -> float:
    return sum(value * right.get(term, 0.0) for term, value in left.items())
