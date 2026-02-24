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

    @classmethod
    def log_mark_deleted(cls, request, mark) -> None:
        log_event(
            action=AuditEvents.ATTENDANCE_MARK_DELETED,
            actor=request.user,
            object_type="attendance_mark",
            object_id=str(mark.id),
            level="warning",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "user_id": mark.user_id,
                "date": mark.date.isoformat(),
            },
        )

    @classmethod
    def log_work_calendar_day_created(cls, request, day) -> None:
        log_event(
            action=AuditEvents.WORK_CALENDAR_DAY_CREATED,
            actor=request.user,
            object_type="work_calendar_day",
            object_id=day.date.isoformat(),
            level="info",
            category="content",
            ip_address=cls._ip(request),
        )

    @classmethod
    def log_work_calendar_day_updated(cls, request, day, changed_fields: list[str]) -> None:
        log_event(
            action=AuditEvents.WORK_CALENDAR_DAY_UPDATED,
            actor=request.user,
            object_type="work_calendar_day",
            object_id=day.date.isoformat(),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={"changed_fields": sorted(changed_fields)},
        )

    @classmethod
    def log_work_calendar_day_deleted(cls, request, day_date) -> None:
        log_event(
            action=AuditEvents.WORK_CALENDAR_DAY_DELETED,
            actor=request.user,
            object_type="work_calendar_day",
            object_id=day_date.isoformat(),
            level="warning",
            category="content",
            ip_address=cls._ip(request),
        )

    @classmethod
    def log_work_calendar_month_generated(cls, request, year: int, month: int, created: int, updated: int) -> None:
        log_event(
            action=AuditEvents.WORK_CALENDAR_MONTH_GENERATED,
            actor=request.user,
            object_type="work_calendar_month",
            object_id=f"{year:04d}-{month:02d}",
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={"created": created, "updated": updated},
        )

    @classmethod
    def log_office_checkin_in_office(cls, request, session) -> None:
        log_event(
            action=AuditEvents.ATTENDANCE_OFFICE_CHECKIN_IN_OFFICE,
            actor=request.user,
            object_type="attendance_session",
            object_id=str(session.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "distance_m": round(float(session.distance_m), 2),
                "radius_m": session.radius_m,
            },
        )

    @classmethod
    def log_office_checkin_outside(cls, request, session) -> None:
        log_event(
            action=AuditEvents.ATTENDANCE_OFFICE_CHECKIN_OUTSIDE,
            actor=request.user,
            object_type="attendance_session",
            object_id=str(session.id),
            level="warning",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "distance_m": round(float(session.distance_m), 2),
                "radius_m": session.radius_m,
            },
        )
