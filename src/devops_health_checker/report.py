import json
import os
from datetime import UTC, datetime
from pathlib import Path

from devops_health_checker.models import (
    HealthResult,
    HealthStatus,
)


def _default_report_path() -> str:
    """Return a writable default path.

    Inside a container with readOnlyRootFilesystem=true the only writable
    location is /tmp.  Outside (local dev) we keep the original reports/ dir.
    """
    env_path = os.getenv("REPORT_OUTPUT_PATH")
    if env_path:
        return env_path

    # If running inside a container use /tmp; otherwise use project-relative reports/
    if os.path.exists("/.dockerenv") or os.getenv("KUBERNETES_SERVICE_HOST"):
        return "/tmp/reports/health-report.json"

    return "reports/health-report.json"


def calculate_overall_status(components: list[HealthResult]) -> HealthStatus:
    if not components:
        return HealthStatus.UNKNOWN

    statuses = [c.status for c in components]

    if HealthStatus.CRITICAL in statuses:
        return HealthStatus.CRITICAL
    if HealthStatus.WARNING in statuses:
        return HealthStatus.WARNING
    if HealthStatus.UNKNOWN in statuses:
        return HealthStatus.UNKNOWN
    if all(s == HealthStatus.HEALTHY for s in statuses):
        return HealthStatus.HEALTHY

    return HealthStatus.UNKNOWN


def generate_report(
    components: list[HealthResult],
    output_path: str | None = None,
) -> dict:
    overall_status = calculate_overall_status(components)

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "overall_status": overall_status.value,
        "components": {component.name: component.to_dict() for component in components},
    }

    resolved_path = Path(output_path or _default_report_path())
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    with resolved_path.open("w") as fh:
        json.dump(report, fh, indent=4)

    return report
