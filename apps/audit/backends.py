from __future__ import annotations

from typing import Protocol

from .contracts import AuditEvent


class AuditBackend(Protocol):
    def write(self, event: AuditEvent) -> None:
        ...


class AccountsAuditBackend:
    """
    Primary backend.
    Writes to existing accounts.AuditLog table without schema changes.
    """

    def write(self, event: AuditEvent) -> None:
        from accounts.models import AuditLog

        AuditLog.log(
            action=event.action,
            user=event.actor,
            object_type=event.object_type,
            object_id=event.object_id,
            level=event.level,
            category=event.category,
            ip_address=event.ip_address,
        )


class SecuritySystemLogBackend:
    """
    Legacy backend.
    Kept only for backward compatibility during migration.
    """

    def write(self, event: AuditEvent) -> None:
        from security.models import SystemLog

        SystemLog.objects.create(
            actor=event.actor,
            action=event.action,
            level=event.level,
            metadata=event.metadata or {},
        )


class NoopAuditBackend:
    def write(self, event: AuditEvent) -> None:  # pragma: no cover
        return None

