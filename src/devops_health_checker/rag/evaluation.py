from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from devops_health_checker.rag.search import SearchResult


@dataclass(frozen=True)
class RetrievalCase:
    query: str
    expected_sources: tuple[str, ...]


@dataclass(frozen=True)
class AgentEvaluationCase:
    prompt: str
    expected_phrases: tuple[str, ...] = ()
    expected_sources: tuple[str, ...] = ()


def evaluate_retrieval(
    search: Callable[[str, int], list[SearchResult]],
    cases: Sequence[RetrievalCase],
    top_k: int = 5,
) -> dict[str, Any]:
    """Evaluate source retrieval with precision, recall, and hit rate."""
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    if not cases:
        return {
            "queries": 0,
            "precision_at_k": 0.0,
            "recall": 0.0,
            "hit_rate": 0.0,
        }

    relevant_results = 0
    expected_source_count = 0
    successful_queries = 0

    for case in cases:
        expected_sources = set(case.expected_sources)
        expected_source_count += len(expected_sources)
        results = search(case.query, top_k)
        result_sources = {result.chunk.source for result in results}
        matches = result_sources & expected_sources
        relevant_results += len(matches)
        if matches:
            successful_queries += 1

    query_count = len(cases)
    precision = relevant_results / (query_count * top_k)
    recall = relevant_results / expected_source_count if expected_source_count else 0.0

    return {
        "queries": query_count,
        "precision_at_k": round(precision, 6),
        "recall": round(recall, 6),
        "hit_rate": round(successful_queries / query_count, 6),
    }


def evaluate_agent(agent, cases: Sequence[AgentEvaluationCase]) -> dict[str, Any]:
    """Evaluate deterministic answer expectations for a small test dataset."""
    if not cases:
        return {"cases": 0, "passed": 0, "pass_rate": 0.0}

    passed = 0
    details = []
    for case in cases:
        answer = agent.run(case.prompt)
        normalized_answer = answer.lower()
        phrases_match = all(phrase.lower() in normalized_answer for phrase in case.expected_phrases)
        sources_match = all(source.lower() in normalized_answer for source in case.expected_sources)
        case_passed = phrases_match and sources_match
        passed += int(case_passed)
        details.append({"prompt": case.prompt, "passed": case_passed})

    return {
        "cases": len(cases),
        "passed": passed,
        "pass_rate": round(passed / len(cases), 6),
        "details": details,
    }
