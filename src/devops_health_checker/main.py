import argparse
import json
from concurrent.futures import ThreadPoolExecutor

from devops_health_checker.agent import DevOpsAgent
from devops_health_checker.api import run_api_server
from devops_health_checker.config import (
    get_github_config,
    get_kubernetes_config,
    get_llm_config,
    load_config,
)
from devops_health_checker.llm import OpenRouterClient
from devops_health_checker.logger import setup_logger
from devops_health_checker.mcp import MCPServer, run_stdio_server
from devops_health_checker.multi_agent import MultiAgentCoordinator
from devops_health_checker.report import generate_report
from devops_health_checker.timing import measure_time
from devops_health_checker.tools.registry import create_tool_registry

logger = setup_logger()


def parse_arguments():
    parser = argparse.ArgumentParser(description="DevOps Infrastructure Health Checker")

    parser.add_argument("--github", action="store_true", help="Run GitHub health check")
    parser.add_argument("--aws", action="store_true", help="Run AWS health check")
    parser.add_argument("--kubernetes", action="store_true", help="Run Kubernetes health check")
    parser.add_argument("--all", action="store_true", help="Run all health checks (parallel)")

    parser.add_argument(
        "--agent",
        type=str,
        help="Ask the AI DevOps agent a question about infrastructure",
    )
    parser.add_argument(
        "--knowledge",
        type=str,
        help="Search the local DevOps knowledge base without using the AI agent",
    )
    parser.add_argument("--list-tools", action="store_true", help="List available tools")
    parser.add_argument("--list-schemas", action="store_true", help="List schemas for tools")
    parser.add_argument(
        "--mcp-server",
        action="store_true",
        help="Run the tools through an MCP-compatible stdio server",
    )
    parser.add_argument("--api-server", action="store_true", help="Run the HTTP API server")
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


# ─── Individual check runners ─────────────────────────────────────────────────


def run_github_check(registry, config):
    github_config = get_github_config(config)
    owner = github_config.get("owner", "kubernetes")
    repository = github_config.get("repository", "kubernetes")
    result, duration_ms = measure_time(
        registry.run, "github_repository", owner=owner, repository=repository
    )
    return result, duration_ms


def run_aws_check(registry):
    return measure_time(registry.run, "aws_ec2_health")


def run_kubernetes_check(registry, config):
    kubernetes_config = get_kubernetes_config(config)
    namespace = kubernetes_config.get("namespace")
    return measure_time(registry.run, "kubernetes_health", namespace=namespace)


# ─── Parallel runner ──────────────────────────────────────────────────────────


def run_checks_parallel(registry, config, run_github: bool, run_aws: bool, run_kubernetes: bool):
    """Execute selected health checks concurrently and return results in order."""
    task_map = {}
    components = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        if run_github:
            task_map["github"] = executor.submit(run_github_check, registry, config)
        if run_aws:
            task_map["aws"] = executor.submit(run_aws_check, registry)
        if run_kubernetes:
            task_map["kubernetes"] = executor.submit(run_kubernetes_check, registry, config)

        for name, future in task_map.items():
            try:
                result, duration_ms = future.result()
                result.duration_ms = duration_ms
                components.append(result)
                logger.info(
                    "Health check completed",
                    extra={
                        "component": name,
                        "status": result.status.value,
                        "duration_ms": round(duration_ms, 2),
                    },
                )
            except Exception as error:
                logger.error(
                    "Health check failed",
                    extra={"component": name, "error": str(error)},
                )

    return components


# ─── Mode handlers ────────────────────────────────────────────────────────────


def run_agent(registry, llm_client, user_message):
    logger.info("Starting AI DevOps agent", extra={"message": user_message[:100]})
    agent = DevOpsAgent(registry=registry, llm_client=llm_client)

    try:
        answer = agent.run(user_message)
    except Exception as error:
        logger.error("AI DevOps agent failed", extra={"error": str(error)})
        print(f"Agent error: {error}")
        return 1

    logger.info("AI DevOps agent completed successfully")
    print()
    print(answer)
    return 0


def run_knowledge_search(registry, query):
    try:
        result = registry.run("search_devops_knowledge", query=query)
    except Exception as error:
        logger.error("Knowledge search failed", extra={"error": str(error)})
        print(f"Knowledge search error: {error}")
        return 1

    print(json.dumps(result, indent=2))
    return 0


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    args = parse_arguments()
    config = load_config()
    registry = create_tool_registry()

    # Build LLM client from config (wires config.yaml llm section)
    llm_config = get_llm_config(config)
    try:
        llm_client = OpenRouterClient(
            model=llm_config["model"],
            timeout=llm_config["timeout"],
        )
    except Exception:
        llm_client = None  # Graceful — LLM-dependent modes will fail with a clear error

    logger.info("DevOps health checker started", extra={"env": config.get("env", "development")})

    if args.list_tools:
        print("\nAvailable tools:\n")
        for tool in registry.list_tools():
            print(f"  {tool.name}: {tool.description}")
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
        result = MultiAgentCoordinator(registry, llm_client=llm_client).run(args.multi_agent)
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    if args.aiops:
        components = [c.strip() for c in args.aiops.split(",") if c.strip()]
        execution = registry.execute("aiops_investigate", {"components": components})
        print(json.dumps(execution.to_dict(), indent=2))
        return 0 if execution.success else 1

    if args.agent:
        return run_agent(registry, llm_client, args.agent)

    if args.knowledge:
        return run_knowledge_search(registry, args.knowledge)

    if args.all:
        args.github = True
        args.aws = True
        args.kubernetes = True

    run_github = args.github
    run_aws = args.aws
    run_k8s = args.kubernetes

    if not any([run_github, run_aws, run_k8s]):
        logger.warning("No health check selected")
        print("No health check selected. Use --github, --aws, --kubernetes, or --all.")
        return 0

    components = run_checks_parallel(registry, config, run_github, run_aws, run_k8s)

    if not components:
        print("All health checks failed. Check logs for details.")
        return 1

    report = generate_report(components)

    logger.info(
        "Health report generated",
        extra={"overall_status": report["overall_status"]},
    )

    print(f"Overall status: {report['overall_status']}")
    print(f"Report generated: {report.get('output_path', 'reports/health-report.json')}")
    return 0


if __name__ == "__main__":
    main()
