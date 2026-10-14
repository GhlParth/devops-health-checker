from unittest.mock import Mock, patch

import requests

from devops_health_checker.models import (
    HealthStatus,
)

from devops_health_checker.tools.github import (
    check_github_health,
    get_repository,
)


@patch(
    "devops_health_checker.tools.github.requests.get"
)
def test_get_repository_success(mock_get):
    mock_response = Mock()

    mock_response.json.return_value = {
        "full_name": "kubernetes/kubernetes",
        "stargazers_count": 100000,
    }

    mock_response.raise_for_status.return_value = None

    mock_get.return_value = mock_response

    result = get_repository(
        "kubernetes",
        "kubernetes",
    )

    assert result["success"] is True

    assert (
        result["data"]["full_name"]
        == "kubernetes/kubernetes"
    )

    mock_get.assert_called_once()


@patch(
    "devops_health_checker.tools.github.requests.get"
)
def test_get_repository_timeout(mock_get):
    mock_get.side_effect = (
        requests.exceptions.Timeout()
    )

    result = get_repository(
        "kubernetes",
        "kubernetes",
    )

    assert result["success"] is False
    assert result["data"] is None

    assert (
        "timed out"
        in result["error"]
    )


@patch(
    "devops_health_checker.tools.github.requests.get"
)
def test_get_repository_http_error(mock_get):
    mock_response = Mock()

    mock_response.raise_for_status.side_effect = (
        requests.exceptions.HTTPError(
            "404 Client Error"
        )
    )

    mock_get.return_value = mock_response

    result = get_repository(
        "kubernetes",
        "does-not-exist",
    )

    assert result["success"] is False
    assert result["data"] is None

    assert (
        "HTTP error"
        in result["error"]
    )


@patch(
    "devops_health_checker.tools.github.get_repository"
)
def test_check_github_health(mock_repository):
    mock_repository.return_value = {
        "success": True,
        "data": {
            "full_name": "kubernetes/kubernetes",
            "description": (
                "Production-grade "
                "container orchestration"
            ),
            "stargazers_count": 100000,
            "forks_count": 40000,
            "open_issues_count": 100,
        },
        "error": None,
    }

    result = check_github_health(
        "kubernetes",
        "kubernetes",
    )

    assert result.name == "github"

    assert (
        result.status
        == HealthStatus.HEALTHY
    )

    assert (
        result.details["repository"]
        == "kubernetes/kubernetes"
    )

    assert (
        result.details["stars"]
        == 100000
    )

    assert (
        result.details["forks"]
        == 40000
    )

    assert (
        result.details["open_issues"]
        == 100
    )


@patch(
    "devops_health_checker.tools.github.get_repository"
)
def test_check_github_health_failure(
    mock_repository,
):
    mock_repository.return_value = {
        "success": False,
        "data": None,
        "error": "GitHub API unavailable",
    }

    result = check_github_health(
        "kubernetes",
        "kubernetes",
    )

    assert result.name == "github"

    assert (
        result.status
        == HealthStatus.CRITICAL
    )

    assert (
        "GitHub API unavailable"
        in result.errors[0]
    )