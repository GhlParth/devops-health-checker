from devops_health_checker.models import (
    HealthResult,
    HealthStatus,
)
from devops_health_checker.report import (
    calculate_overall_status,
)


def make_result(name, status):
    return HealthResult(
        name=name,
        status=status,
    )


def test_empty_components_return_unknown():
    result = calculate_overall_status([])

    assert result == HealthStatus.UNKNOWN


def test_all_healthy_returns_healthy():
    components = [
        make_result("github", HealthStatus.HEALTHY),
        make_result("aws", HealthStatus.HEALTHY),
        make_result("kubernetes", HealthStatus.HEALTHY),
    ]

    result = calculate_overall_status(components)

    assert result == HealthStatus.HEALTHY


def test_warning_returns_warning():
    components = [
        make_result("github", HealthStatus.HEALTHY),
        make_result("aws", HealthStatus.WARNING),
        make_result("kubernetes", HealthStatus.HEALTHY),
    ]

    result = calculate_overall_status(components)

    assert result == HealthStatus.WARNING


def test_critical_overrides_warning():
    components = [
        make_result("github", HealthStatus.WARNING),
        make_result("aws", HealthStatus.CRITICAL),
        make_result("kubernetes", HealthStatus.HEALTHY),
    ]

    result = calculate_overall_status(components)

    assert result == HealthStatus.CRITICAL


def test_unknown_without_critical_or_warning():
    components = [
        make_result("github", HealthStatus.UNKNOWN),
        make_result("aws", HealthStatus.HEALTHY),
    ]

    result = calculate_overall_status(components)

    assert result == HealthStatus.UNKNOWN
    