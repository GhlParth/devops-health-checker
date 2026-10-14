from pathlib import Path
from typing import Any

from devops_health_checker.rag.documents import load_documents
from devops_health_checker.rag.vector_store import TfidfVectorStore

KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "knowledge"
_cached_signature: tuple[tuple[str, int, int], ...] | None = None
_cached_store: TfidfVectorStore | None = None


def search_devops_knowledge(
    query: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """Search the read-only local DevOps knowledge base."""
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not query.strip():
        raise ValueError("query must not be empty")

    store = _get_store()
    results = store.search(query, top_k)

    return {
        "query": query,
        "match_count": len(results),
        "results": [
            {
                "content": result.chunk.content,
                "source": result.chunk.source,
                "category": result.chunk.category,
                "chunk_index": result.chunk.chunk_index,
                "score": round(result.score, 6),
                "matched_terms": list(result.matched_terms),
            }
            for result in results
        ],
    }


def _get_store() -> TfidfVectorStore:
    global _cached_signature, _cached_store

    signature = _knowledge_signature()
    if _cached_store is None or signature != _cached_signature:
        documents = load_documents(str(KNOWLEDGE_DIR))
        _cached_store = TfidfVectorStore.from_documents(documents)
        _cached_signature = signature

    return _cached_store


def _knowledge_signature() -> tuple[tuple[str, int, int], ...]:
    if not KNOWLEDGE_DIR.exists():
        return ()

    files = []
    for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
        stat = path.stat()
        files.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(files)
