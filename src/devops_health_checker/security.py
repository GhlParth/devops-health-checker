from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    timestamp: str
    event: str
    tool_name: str
    success: bool | None
    argument_names: tuple[str, ...] = ()
    error: str | None = None


@dataclass
class AuditLog:
    events: list[AuditEvent] = field(default_factory=list)

    def record(
        self,
        event: str,
        tool_name: str,
        success: bool | None = None,
        arguments: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        self.events.append(
            AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event=event,
                tool_name=tool_name,
                success=success,
                argument_names=tuple(sorted(arguments or {})),
                error=error,
            )
        )


class ToolApprovalRequired(PermissionError):
    """Raised when a write-capable tool lacks host approval."""


def validate_tool_policy(tool, approved: bool) -> None:
    if tool.requires_approval and not approved:
        raise ToolApprovalRequired(
            f"Tool '{tool.name}' requires explicit approval before execution."
        )
