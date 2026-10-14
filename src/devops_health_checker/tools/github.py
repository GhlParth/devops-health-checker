import requests

from devops_health_checker.models import (
    HealthResult,
    HealthStatus,
)


def get_repository(owner, repository):
    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repository}"
    )

    try:
        response = requests.get(
            url,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        return {
            "success": True,
            "data": data,
            "error": None,
        }

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
            "error": (
                f"GitHub API returned HTTP error: "
                f"{error}"
            ),
        }

    except requests.exceptions.RequestException as error:
        return {
            "success": False,
            "data": None,
            "error": (
                f"GitHub API request failed: "
                f"{error}"
            ),
        }


def check_github_health(
    owner="kubernetes",
    repository="kubernetes",
):
    result = get_repository(
        owner,
        repository,
    )

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
            "description": data.get(
                "description"
            ),
            "stars": data.get(
                "stargazers_count",
                0,
            ),
            "forks": data.get(
                "forks_count",
                0,
            ),
            "open_issues": data.get(
                "open_issues_count",
                0,
            ),
        },
        errors=[],
    )