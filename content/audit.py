from __future__ import annotations

from typing import Optional

from apps.audit import AuditEvents, log_event


class ContentAuditService:
    @staticmethod
    def _ip(request) -> Optional[str]:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @classmethod
    def log_feedback_created(cls, request, feedback) -> None:
        log_event(
            action=AuditEvents.FEEDBACK_CREATED,
            actor=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
            object_type="feedback",
            object_id=str(feedback.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "feedback_id": str(feedback.id),
                "type": feedback.type,
                "is_anonymous": feedback.is_anonymous,
                "status": feedback.status,
            },
        )

    @classmethod
    def log_feedback_updated_admin(cls, request, feedback, changed_fields: list[str]) -> None:
        log_event(
            action=AuditEvents.FEEDBACK_UPDATED_ADMIN,
            actor=request.user,
            object_type="feedback",
            object_id=str(feedback.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "feedback_id": str(feedback.id),
                "changed_fields": changed_fields,
            },
        )

    @classmethod
    def log_feedback_status_changed_admin(cls, request, feedback, from_status: str, to_status: str) -> None:
        log_event(
            action=AuditEvents.FEEDBACK_STATUS_CHANGED_ADMIN,
            actor=request.user,
            object_type="feedback",
            object_id=str(feedback.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "feedback_id": str(feedback.id),
                "from_status": from_status,
                "to_status": to_status,
            },
        )
