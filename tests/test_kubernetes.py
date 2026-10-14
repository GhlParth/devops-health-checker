from unittest.mock import Mock, patch

from devops_health_checker.tools.kubernetes import (
    check_kubernetes_health,
    get_nodes,
    get_pods,
)


@patch(
    "devops_health_checker.tools.kubernetes.config.load_kube_config"
)
@patch(
    "devops_health_checker.tools.kubernetes.client.CoreV1Api"
)
def test_get_nodes(
    mock_api,
    mock_config,
):
    node = Mock()

    node.metadata.name = (
        "kind-control-plane"
    )

    condition = Mock()

    condition.type = "Ready"
    condition.status = "True"

    node.status.conditions = [
        condition
    ]

    mock_v1 = Mock()

    mock_v1.list_node.return_value.items = [
        node
    ]

    mock_api.return_value = mock_v1

    result = get_nodes()

    assert len(result) == 1

    assert (
        result[0]["name"]
        == "kind-control-plane"
    )

    assert result[0]["ready"] is True


@patch(
    "devops_health_checker.tools.kubernetes.config.load_kube_config"
)
@patch(
    "devops_health_checker.tools.kubernetes.client.CoreV1Api"
)
def test_get_pods_all_namespaces(
    mock_api,
    mock_config,
):
    pod = Mock()

    pod.metadata.name = "nginx"
    pod.metadata.namespace = "default"
    pod.status.phase = "Running"

    mock_v1 = Mock()

    (
        mock_v1
        .list_pod_for_all_namespaces
        .return_value.items
    ) = [pod]

    mock_api.return_value = mock_v1

    result = get_pods()

    assert len(result) == 1

    assert (
        result[0]["name"]
        == "nginx"
    )

    assert (
        result[0]["namespace"]
        == "default"
    )

    assert (
        result[0]["phase"]
        == "Running"
    )


@patch(
    "devops_health_checker.tools.kubernetes.get_nodes"
)
@patch(
    "devops_health_checker.tools.kubernetes.get_pods"
)
def test_kubernetes_health_healthy(
    mock_pods,
    mock_nodes,
):
    mock_nodes.return_value = [
        {
            "name": "kind-control-plane",
            "ready": True,
        }
    ]

    mock_pods.return_value = [
        {
            "name": "nginx",
            "namespace": "default",
            "phase": "Running",
        }
    ]

    result = check_kubernetes_health()

    assert (
        result.status.value
        == "HEALTHY"
    )

    assert (
        result.details["total_nodes"]
        == 1
    )

    assert (
        result.details["total_pods"]
        == 1
    )


@patch(
    "devops_health_checker.tools.kubernetes.get_nodes"
)
@patch(
    "devops_health_checker.tools.kubernetes.get_pods"
)
def test_kubernetes_health_unhealthy_node(
    mock_pods,
    mock_nodes,
):
    mock_nodes.return_value = [
        {
            "name": "kind-control-plane",
            "ready": False,
        }
    ]

    mock_pods.return_value = []

    result = check_kubernetes_health()

    assert (
        result.status.value
        == "CRITICAL"
    )

    assert (
        result.details[
            "unhealthy_nodes"
        ]
        == 1
    )


@patch(
    "devops_health_checker.tools.kubernetes.get_nodes"
)
@patch(
    "devops_health_checker.tools.kubernetes.get_pods"
)
def test_kubernetes_health_unhealthy_pod(
    mock_pods,
    mock_nodes,
):
    mock_nodes.return_value = [
        {
            "name": "kind-control-plane",
            "ready": True,
        }
    ]

    mock_pods.return_value = [
        {
            "name": "broken-app",
            "namespace": "default",
            "phase": "Failed",
        }
    ]

    result = check_kubernetes_health()

    assert (
        result.status.value
        == "WARNING"
    )

    assert (
        result.details[
            "unhealthy_pods"
        ]
        == 1
    )


@patch(
    "devops_health_checker.tools.kubernetes.get_nodes"
)
def test_kubernetes_health_failure(
    mock_nodes,
):
    mock_nodes.side_effect = Exception(
        "Kubernetes API unavailable"
    )

    result = check_kubernetes_health()

    assert (
        result.status.value
        == "CRITICAL"
    )

    assert len(result.errors) == 1

    assert (
        "Kubernetes API unavailable"
        in result.errors[0]
    )