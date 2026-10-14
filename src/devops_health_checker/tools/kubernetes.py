from kubernetes import client, config

from devops_health_checker.models import (
    HealthResult,
    HealthStatus,
)


def load_kubernetes_config():
    config.load_kube_config()


def get_nodes():
    load_kubernetes_config()

    v1 = client.CoreV1Api()

    response = v1.list_node()

    nodes = []

    for node in response.items:
        ready = False

        for condition in (
            node.status.conditions or []
        ):
            if condition.type == "Ready":
                ready = (
                    condition.status
                    == "True"
                )

        nodes.append(
            {
                "name": node.metadata.name,
                "ready": ready,
            }
        )

    return nodes


def get_pods(namespace=None):
    load_kubernetes_config()

    v1 = client.CoreV1Api()

    if namespace:
        response = (
            v1.list_namespaced_pod(
                namespace=namespace
            )
        )

    else:
        response = (
            v1.list_pod_for_all_namespaces()
        )

    pods = []

    for pod in response.items:
        pods.append(
            {
                "name": pod.metadata.name,
                "namespace": (
                    pod.metadata.namespace
                ),
                "phase": pod.status.phase,
            }
        )

    return pods


def check_kubernetes_health(
    namespace=None,
):
    try:
        nodes = get_nodes()

        pods = get_pods(
            namespace
        )

    except Exception as error:
        return HealthResult(
            name="kubernetes",
            status=HealthStatus.CRITICAL,
            details={},
            errors=[
                (
                    "Kubernetes health check "
                    f"failed: {error}"
                )
            ],
        )

    unhealthy_nodes = [
        node
        for node in nodes
        if not node["ready"]
    ]

    unhealthy_pods = [
        pod
        for pod in pods
        if pod["phase"]
        not in [
            "Running",
            "Succeeded",
        ]
    ]

    if unhealthy_nodes:
        status = HealthStatus.CRITICAL

    elif unhealthy_pods:
        status = HealthStatus.WARNING

    else:
        status = HealthStatus.HEALTHY

    return HealthResult(
        name="kubernetes",
        status=status,
        details={
            "namespace": namespace,
            "total_nodes": len(nodes),
            "unhealthy_nodes": len(
                unhealthy_nodes
            ),
            "total_pods": len(pods),
            "unhealthy_pods": len(
                unhealthy_pods
            ),
            "nodes": nodes,
            "pods": pods,
        },
        errors=[],
    )