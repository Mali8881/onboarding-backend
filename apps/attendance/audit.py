from __future__ import annotations

from typing import Optional

from apps.audit import AuditEvents, log_event


class AttendanceAuditService:
    @staticmethod
    def _ip(request) -> Optional[str]:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @classmethod
    def log_mark_created(cls, request, mark) -> None:
        log_event(
            action=AuditEvents.ATTENDANCE_MARK_CREATED,
            actor=request.user,
            object_type="attendance_mark",
            object_id=str(mark.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "user_id": mark.user_id,
                "date": mark.date.isoformat(),
                "status": mark.status,
            },
        )

    @classmethod
    def log_mark_updated(cls, request, mark, changed_fields: list[str]) -> None:
        log_event(
            action=AuditEvents.ATTENDANCE_MARK_UPDATED,
            actor=request.user,
            object_type="attendance_mark",
            object_id=str(mark.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "user_id": mark.user_id,
                "date": mark.date.isoformat(),
                "changed_fields": changed_fields,
            },
        )

    @classmethod
    def log_mark_change_denied(cls, request, target_user_id: int, mark_date) -> None:
        log_event(
            action=AuditEvents.ATTENDANCE_MARK_CHANGE_DENIED,
            actor=request.user,
            object_type="attendance_mark",
            object_id="",
            level="warning",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "target_user_id": target_user_id,
                "date": mark_date.isoformat(),
            },
        )

