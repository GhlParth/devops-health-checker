from devops_health_checker.models import (
    HealthResult,
    HealthStatus,
)


def test_health_result_to_dict():
    result = HealthResult(
        name="aws",
        status=HealthStatus.HEALTHY,
        details={
            "total_instances": 2,
        },
        errors=[],
        duration_ms=125.4567,
    )

    data = result.to_dict()

    assert data["name"] == "aws"
    assert data["status"] == "HEALTHY"
    assert data["details"]["total_instances"] == 2
    assert data["errors"] == []
    assert data["duration_ms"] == 125.46