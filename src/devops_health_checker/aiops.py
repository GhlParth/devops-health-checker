from typing import Any, Callable


def create_aiops_investigator(registry) -> Callable[..., dict[str, Any]]:
    """Create a read-only anomaly investigator bound to the tool registry."""
    from devops_health_checker.tools.integration import (
        create_agentic_review_tool,
    )

    review = create_agentic_review_tool(registry)

    def investigate(
        components: list[str],
        namespace: str | None = None,
        owner: str | None = None,
        repository: str | None = None,
        knowledge_query: str | None = None,
        top_k: int = 3,
    ) -> dict[str, Any]:
        review_result = review(
            components,
            namespace=namespace,
            owner=owner,
            repository=repository,
            knowledge_query=knowledge_query,
            top_k=top_k,
        )
        incidents = []
        proposals = []

        for component, execution in review_result["health_results"].items():
            if not execution.get("success"):
                incidents.append(
                    {
                        "component": component,
                        "severity": "unknown",
                        "type": "provider_failure",
                        "evidence": execution.get("error"),
                    }
                )
                proposals.append(_proposal(component, "inspect provider access"))
                continue

            result = execution.get("result") or {}
            status = result.get("status", "UNKNOWN")
            if status == "HEALTHY":
                continue

            incidents.append(
                {
                    "component": component,
                    "severity": status.lower(),
                    "type": "health_anomaly",
                    "evidence": {
                        "details": result.get("details", {}),
                        "errors": result.get("errors", []),
                    },
                }
            )
            proposals.extend(_proposals_for_component(component))

        return {
            "incidents": incidents,
            "guidance": review_result["guidance"],
            "proposals": proposals,
            "automation": {
                "enabled": False,
                "executed_actions": [],
                "reason": "All remediation requires explicit host approval.",
            },
        }

    return investigate


def _proposals_for_component(component: str) -> list[dict[str, Any]]:
    actions = {
        "kubernetes": [
            "inspect pod events and current logs",
            "inspect previous container logs",
            "review resource limits and probes",
        ],
        "aws": [
            "inspect affected instance state and recent events",
            "review IAM and security-group changes",
        ],
        "github": [
            "inspect recent repository and workflow changes",
            "review failed CI job logs",
        ],
    }
    return [
        _proposal(component, action)
        for action in actions.get(component, ["collect provider diagnostics"])
    ]


def _proposal(component: str, action: str) -> dict[str, Any]:
    return {
        "component": component,
        "action": action,
        "executed": False,
        "requires_approval": True,
    }
