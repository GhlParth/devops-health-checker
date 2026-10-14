import json
from datetime import datetime, timezone
from pathlib import Path

from devops_health_checker.models import (
    HealthResult,
    HealthStatus,
)


def calculate_overall_status(
    components,
):
    if not components:
        return HealthStatus.UNKNOWN

    statuses = [
        component.status
        for component in components
    ]

    if HealthStatus.CRITICAL in statuses:
        return HealthStatus.CRITICAL

    if HealthStatus.WARNING in statuses:
        return HealthStatus.WARNING

    if HealthStatus.UNKNOWN in statuses:
        return HealthStatus.UNKNOWN

    if all(
        status == HealthStatus.HEALTHY
        for status in statuses
    ):
        return HealthStatus.HEALTHY

    return HealthStatus.UNKNOWN


def generate_report(
    components: list[HealthResult],
    output_path="reports/health-report.json",
):
    overall_status = calculate_overall_status(
        components
    )

    report = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "overall_status": overall_status.value,
        "components": {
            component.name: component.to_dict()
            for component in components
        },
    }

    output_file = Path(output_path)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_file.open("w") as file:
        json.dump(
            report,
            file,
            indent=4,
        )

    return report