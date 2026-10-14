from collections.abc import Callable
from typing import Any

SUPPORTED_COMPONENTS = {
    "aws": "aws_ec2_health",
    "kubernetes": "kubernetes_health",
    "github": "github_repository",
}


def create_agentic_review_tool(registry) -> Callable[..., dict[str, Any]]:
    """Create a read-only multi-provider review bound to a tool registry."""

    def run_agentic_review(
        components: list[str],
        namespace: str | None = None,
        owner: str | None = None,
        repository: str | None = None,
        knowledge_query: str | None = None,
        top_k: int = 3,
    ) -> dict[str, Any]:
        if not components:
            raise ValueError("components must contain at least one component")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        unknown_components = sorted(set(components) - set(SUPPORTED_COMPONENTS))
        if unknown_components:
            raise ValueError("Unsupported component(s): " + ", ".join(unknown_components))

        health_results: dict[str, Any] = {}
        guidance: list[dict[str, Any]] = []

        for component in dict.fromkeys(components):
            arguments = _component_arguments(
                component,
                namespace=namespace,
                owner=owner,
                repository=repository,
            )
            execution = registry.execute(
                SUPPORTED_COMPONENTS[component],
                arguments,
            )
            health_results[component] = execution.to_dict()

        query = knowledge_query or _build_knowledge_query(health_results)
        if query:
            knowledge_execution = registry.execute(
                "search_devops_knowledge",
                {"query": query, "top_k": top_k},
            )
            if knowledge_execution.success:
                guidance = knowledge_execution.result.get("results", [])
            else:
                guidance = [{"error": knowledge_execution.error}]

        return {
            "components": list(dict.fromkeys(components)),
            "health_results": health_results,
            "knowledge_query": query,
            "guidance": guidance,
        }

    return run_agentic_review


def _component_arguments(
    component: str,
    *,
    namespace: str | None,
    owner: str | None,
    repository: str | None,
) -> dict[str, Any]:
    if component == "kubernetes":
        return {"namespace": namespace}
    if component == "github":
        if not owner or not repository:
            raise ValueError("owner and repository are required for github")
        return {"owner": owner, "repository": repository}
    return {}


def _build_knowledge_query(health_results: dict[str, Any]) -> str:
    terms = []
    for component, execution in health_results.items():
        result = execution.get("result") or {}
        status = result.get("status", "unknown")
        errors = " ".join(result.get("errors", []))
        terms.append(f"{component} {status} {errors}".strip())
    return " ".join(terms)
