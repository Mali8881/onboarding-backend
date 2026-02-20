from __future__ import annotations

from typing import Optional

from apps.audit import AuditEvents, log_event


class CommonAuditService:
    @staticmethod
    def _ip(request) -> Optional[str]:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @classmethod
    def log_notification_marked_read(cls, request, notification) -> None:
        log_event(
            action=AuditEvents.NOTIFICATION_MARKED_READ,
            actor=request.user,
            object_type="notification",
            object_id=str(notification.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "notification_id": notification.id,
            },
        )

    @classmethod
    def log_notifications_marked_read_all(cls, request, updated_count: int) -> None:
        log_event(
            action=AuditEvents.NOTIFICATIONS_MARKED_READ_ALL,
            actor=request.user,
            object_type="notification",
            object_id="",
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "updated_count": updated_count,
            },
        )

