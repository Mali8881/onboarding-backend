from __future__ import annotations

from django.conf import settings
from typing import Optional

from .backends import (
    AccountsAuditBackend,
    AuditBackend,
    NoopAuditBackend,
    SecuritySystemLogBackend,
)
from .contracts import AuditEvent


class AuditService:
    """
    Unified entrypoint for audit logging.

    Modes:
    - primary_only (default): write only to primary backend
    - dual_write: write to primary and legacy backends
    - legacy_only: write only to legacy backend
    """

    def __init__(self) -> None:
        self.primary_backend = self._build_backend(
            getattr(settings, "AUDIT_PRIMARY_BACKEND", "accounts")
        )
        self.legacy_backend = self._build_backend(
            getattr(settings, "AUDIT_LEGACY_BACKEND", "security")
        )
        self.mode = getattr(settings, "AUDIT_WRITE_MODE", "primary_only")

    def _build_backend(self, name: str) -> AuditBackend:
        if name == "accounts":
            return AccountsAuditBackend()
        if name == "security":
            return SecuritySystemLogBackend()
        return NoopAuditBackend()

    def log(self, event: AuditEvent) -> None:
        try:
            if self.mode == "legacy_only":
                self.legacy_backend.write(event)
                return

            self.primary_backend.write(event)

            if self.mode == "dual_write":
                self.legacy_backend.write(event)
        except Exception:
            # Audit should not break main request flow.
            return


def log_event(
    *,
    action: str,
    actor=None,
    object_type: str = "",
    object_id: str = "",
    level: str = "info",
    category: str = "system",
    ip_address: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    event = AuditEvent(
        action=action,
        actor=actor,
        object_type=object_type,
        object_id=object_id,
        level=level,
        category=category,
        ip_address=ip_address,
        metadata=metadata,
    )
    AuditService().log(event)
