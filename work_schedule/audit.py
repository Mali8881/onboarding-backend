from __future__ import annotations

from typing import Optional

from apps.audit import AuditEvents, log_event


class WorkScheduleAuditService:
    @staticmethod
    def _ip(request) -> Optional[str]:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @classmethod
    def log_schedule_selection_invalid_payload(cls, request) -> None:
        log_event(
            action=AuditEvents.SCHEDULE_SELECTION_INVALID_PAYLOAD,
            actor=request.user,
            object_type="work_schedule",
            object_id="",
            level="warning",
            category="content",
            ip_address=cls._ip(request),
            metadata={"actor_id": request.user.id},
        )

    @classmethod
    def log_schedule_selection_not_found(cls, request, schedule_id) -> None:
        log_event(
            action=AuditEvents.SCHEDULE_SELECTION_NOT_FOUND,
            actor=request.user,
            object_type="work_schedule",
            object_id=str(schedule_id or ""),
            level="warning",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "schedule_id": str(schedule_id or ""),
            },
        )

    @classmethod
    def log_schedule_selected_for_approval(cls, request, schedule, was_created: bool) -> None:
        log_event(
            action=AuditEvents.SCHEDULE_SELECTED_FOR_APPROVAL,
            actor=request.user,
            object_type="work_schedule",
            object_id=str(schedule.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "schedule_id": schedule.id,
                "schedule_name": schedule.name,
                "assignment_created": was_created,
            },
        )
