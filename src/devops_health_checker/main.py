import argparse
import json

from devops_health_checker.agent import DevOpsAgent
from devops_health_checker.api import run_api_server
from devops_health_checker.config import (
    get_github_config,
    get_kubernetes_config,
    load_config,
)
from devops_health_checker.logger import setup_logger
from devops_health_checker.mcp import MCPServer, run_stdio_server
from devops_health_checker.multi_agent import MultiAgentCoordinator
from devops_health_checker.report import generate_report
from devops_health_checker.timing import measure_time
from devops_health_checker.tools.registry import (
    create_tool_registry,
)


logger = setup_logger()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="DevOps Infrastructure Health Checker"
    )

    parser.add_argument(
        "--github",
        action="store_true",
        help="Run GitHub health check",
    )

    parser.add_argument(
        "--aws",
        action="store_true",
        help="Run AWS health check",
    )

    parser.add_argument(
        "--kubernetes",
        action="store_true",
        help="Run Kubernetes health check",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all health checks",
    )

    parser.add_argument(
        "--agent",
        type=str,
        help=(
            "Ask the AI DevOps agent a "
            "question about infrastructure"
        ),
    )

    parser.add_argument(
        "--knowledge",
        type=str,
        help=(
            "Search the local DevOps knowledge base "
            "without using the AI agent"
        ),
    )

    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List available health-check tools",
    )

    parser.add_argument(
        "--list-schemas",
        action="store_true",
        help="List schemas for available tools",
    )

    parser.add_argument(
        "--mcp-server",
        action="store_true",
        help="Run the tools through an MCP-compatible stdio server",
    )

    parser.add_argument(
        "--api-server",
        action="store_true",
        help="Run the HTTP API server",
    )

    parser.add_argument(
        "--multi-agent",
        type=str,
        help="Ask routed specialist agents for an infrastructure assessment",
    )

    parser.add_argument(
        "--aiops",
        type=str,
        help="Investigate a component list, for example 'kubernetes,aws'",
    )

    return parser.parse_args()


def run_github_check(
    registry,
    config,
):
    github_config = get_github_config(config)

    owner = github_config.get(
        "owner",
        "kubernetes",
    )

    repository = github_config.get(
        "repository",
        "kubernetes",
    )

    result, duration_ms = measure_time(
        registry.run,
        "github_repository",
        owner=owner,
        repository=repository,
    )

    return result, duration_ms


def run_aws_check(registry):
    return measure_time(
        registry.run,
        "aws_ec2_health",
    )


def run_kubernetes_check(
    registry,
    config,
):
    kubernetes_config = get_kubernetes_config(
        config
    )

    namespace = kubernetes_config.get(
        "namespace"
    )

    return measure_time(
        registry.run,
        "kubernetes_health",
        namespace=namespace,
    )


def run_agent(
    registry,
    user_message,
):
    logger.info(
        "Starting AI DevOps agent"
    )

    logger.info(
        "Agent request: %s",
        user_message,
    )

    agent = DevOpsAgent(
        registry=registry,
    )

    try:
        answer = agent.run(
            user_message
        )

    except Exception as error:
        logger.error(
            "AI DevOps agent failed: %s",
            error,
        )

        print(
            "Agent error: "
            f"{error}"
        )

        return 1

    logger.info(
        "AI DevOps agent completed successfully"
    )

    print()
    print(answer)

    return 0


def run_knowledge_search(
    registry,
    query,
):
    try:
        result = registry.run(
            "search_devops_knowledge",
            query=query,
        )

    except Exception as error:
        logger.error(
            "Knowledge search failed: %s",
            error,
        )
        print(f"Knowledge search error: {error}")
        return 1

    print(json.dumps(result, indent=2))
    return 0


def main():
    args = parse_arguments()

    config = load_config()

    registry = create_tool_registry()

    logger.info(
        "Starting DevOps health checker"
    )

    if args.list_tools:
        print("\nAvailable tools:\n")

        for tool in registry.list_tools():
            print(
                f"{tool.name}: "
                f"{tool.description}"
            )

        return 0

    if args.list_schemas:
        print("\nAvailable tool schemas:\n")

        for schema in registry.list_schemas():
            print(schema.to_dict())

        return 0

    if args.mcp_server:
        run_stdio_server(MCPServer(registry))
        return 0

    if args.api_server:
        run_api_server()
        return 0

    if args.multi_agent:
        result = MultiAgentCoordinator(registry).run(args.multi_agent)
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    if args.aiops:
        components = [
            component.strip()
            for component in args.aiops.split(",")
            if component.strip()
        ]
        execution = registry.execute(
            "aiops_investigate",
            {"components": components},
        )
        print(json.dumps(execution.to_dict(), indent=2))
        return 0 if execution.success else 1

    # AI agent mode.
    #
    # This is intentionally checked before the
    # deterministic health-check flags because
    # --agent represents a separate execution mode.
    if args.agent:
        return run_agent(
            registry,
            args.agent,
        )

    if args.knowledge:
        return run_knowledge_search(
            registry,
            args.knowledge,
        )

    if args.all:
        args.github = True
        args.aws = True
        args.kubernetes = True

    components = []

    if args.github:
        logger.info(
            "Running GitHub health check"
        )

        github_result, duration_ms = (
            run_github_check(
                registry,
                config,
            )
        )

        github_result.duration_ms = (
            duration_ms
        )

        components.append(github_result)

        logger.info(
            "GitHub health check completed | "
            "status=%s | duration=%.2fms",
            github_result.status.value,
            github_result.duration_ms,
        )

    if args.aws:
        logger.info(
            "Running AWS health check"
        )

        aws_result, duration_ms = (
            run_aws_check(registry)
        )

        aws_result.duration_ms = (
            duration_ms
        )

        components.append(aws_result)

        logger.info(
            "AWS health check completed | "
            "status=%s | duration=%.2fms",
            aws_result.status.value,
            aws_result.duration_ms,
        )

    if args.kubernetes:
        logger.info(
            "Running Kubernetes health check"
        )

        kubernetes_result, duration_ms = (
            run_kubernetes_check(
                registry,
                config,
            )
        )

        kubernetes_result.duration_ms = (
            duration_ms
        )

        components.append(
            kubernetes_result
        )

        logger.info(
            "Kubernetes health check completed | "
            "status=%s | duration=%.2fms",
            kubernetes_result.status.value,
            kubernetes_result.duration_ms,
        )

    if not components:
        logger.warning(
            "No health check selected"
        )

        print(
            "No health check selected."
        )

        return 0

    report = generate_report(
        components
    )

    logger.info(
        "Overall health status: %s",
        report["overall_status"],
    )

    logger.info(
        "Health report generated successfully"
    )

    print(
        f"Overall status: "
        f"{report['overall_status']}"
    )

    print(
        "Report generated: "
        "reports/health-report.json"
    )

    return 0


if __name__ == "__main__":
    main()
