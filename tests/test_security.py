import pytest

from devops_health_checker.registry import ToolRegistry
from devops_health_checker.schemas import ToolSchema
from devops_health_checker.security import AuditLog, ToolApprovalRequired


def test_registry_records_audit_events_without_argument_values() -> None:
    audit_log = AuditLog()
    registry = ToolRegistry(audit_log=audit_log)
    registry.register(
        name="safe",
        description="Safe tool.",
        function=lambda token: {"ok": True},
        schema=ToolSchema(
            name="safe",
            description="Safe tool.",
            parameters=[],
        ),
    )

    result = registry.execute("safe", {"token": "secret-value"})

    assert result.success is False
    assert audit_log.events[-1].event == "tool_executed"
    assert audit_log.events[-1].argument_names == ("token",)
    assert "secret-value" not in repr(audit_log.events[-1])


def test_write_capable_tool_requires_host_approval() -> None:
    registry = ToolRegistry()
    registry.register(
        name="mutating",
        description="Mutating tool.",
        function=lambda: "changed",
        schema=ToolSchema(name="mutating", description="Mutating tool."),
        read_only=False,
        requires_approval=True,
    )

    denied = registry.execute("mutating")
    approved = registry.execute("mutating", approved=True)

    assert denied.success is False
    assert "requires explicit approval" in denied.error
    assert approved.success is True


def test_policy_exception_is_available_for_direct_policy_checks() -> None:
    with pytest.raises(ToolApprovalRequired):
        raise ToolApprovalRequired("approval required")
