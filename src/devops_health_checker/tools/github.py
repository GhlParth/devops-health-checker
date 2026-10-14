import os

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from devops_health_checker.models import (
    HealthResult,
    HealthStatus,
)

_RETRYABLE = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)


def _github_headers() -> dict[str, str]:
    """Build GitHub API request headers, including auth token when available."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@retry(
    reraise=True,
    retry=retry_if_exception_type(_RETRYABLE),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
def _fetch_repository(owner: str, repository: str) -> requests.Response:
    url = f"https://api.github.com/repos/{owner}/{repository}"
    return requests.get(url, headers=_github_headers(), timeout=10)


def get_repository(owner: str, repository: str) -> dict:
    try:
        response = _fetch_repository(owner, repository)
        response.raise_for_status()
        return {"success": True, "data": response.json(), "error": None}

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "data": None,
            "error": "GitHub API request timed out",
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "data": None,
            "error": "Unable to connect to GitHub",
        }
    except requests.exceptions.HTTPError as error:
        return {
            "success": False,
            "data": None,
            "error": f"GitHub API returned HTTP error: {error}",
        }
    except requests.exceptions.RequestException as error:
        return {
            "success": False,
            "data": None,
            "error": f"GitHub API request failed: {error}",
        }


def check_github_health(
    owner: str = "kubernetes",
    repository: str = "kubernetes",
) -> HealthResult:
    result = get_repository(owner, repository)

    if not result["success"]:
        return HealthResult(
            name="github",
            status=HealthStatus.CRITICAL,
            details={},
            errors=[result["error"]],
        )

    data = result["data"]

    return HealthResult(
        name="github",
        status=HealthStatus.HEALTHY,
        details={
            "repository": data["full_name"],
            "description": data.get("description"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "default_branch": data.get("default_branch", "main"),
            "archived": data.get("archived", False),
        },
        errors=[],
    )
