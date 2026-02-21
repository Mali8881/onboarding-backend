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

    @classmethod
    def log_work_schedule_created(cls, request, schedule) -> None:
        log_event(
            action=AuditEvents.WORK_SCHEDULE_CREATED,
            actor=request.user,
            object_type="work_schedule",
            object_id=str(schedule.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "schedule_name": schedule.name,
            },
        )

    @classmethod
    def log_work_schedule_updated(cls, request, schedule, changed_fields: list[str]) -> None:
        action = AuditEvents.WORK_SCHEDULE_DEACTIVATED if "is_active" in changed_fields and not schedule.is_active else AuditEvents.WORK_SCHEDULE_UPDATED
        log_event(
            action=action,
            actor=request.user,
            object_type="work_schedule",
            object_id=str(schedule.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "schedule_name": schedule.name,
                "changed_fields": changed_fields,
            },
        )

    @classmethod
    def log_schedule_request_decision(cls, request, assignment, approved: bool) -> None:
        log_event(
            action=AuditEvents.SCHEDULE_REQUEST_APPROVED if approved else AuditEvents.SCHEDULE_REQUEST_REJECTED,
            actor=request.user,
            object_type="user_work_schedule",
            object_id=str(assignment.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "user_id": assignment.user_id,
                "schedule_id": assignment.schedule_id,
                "approved": approved,
            },
        )

    @classmethod
    def log_calendar_month_generated(cls, request, *, year: int, month: int, created: int, updated: int, overwrite: bool) -> None:
        log_event(
            action=AuditEvents.WORK_SCHEDULE_CALENDAR_MONTH_GENERATED,
            actor=request.user,
            object_type="production_calendar",
            object_id=f"{year}-{month:02d}",
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "year": year,
                "month": month,
                "created": created,
                "updated": updated,
                "overwrite": overwrite,
            },
        )
