from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class HealthResult:
    name: str
    status: HealthStatus
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status.value,
            "details": self.details,
            "errors": self.errors,
            "duration_ms": round(
                self.duration_ms,
                2,
            ),
        }
