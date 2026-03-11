from __future__ import annotations

from typing import Optional

from apps.audit import AuditEvents, log_event


class ReportsAuditService:
    @staticmethod
    def _ip(request) -> Optional[str]:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @classmethod
    def log_report_submitted(cls, request, report) -> None:
        log_event(
            action=AuditEvents.REPORT_SUBMITTED,
            actor=request.user,
            object_type="onboarding_report",
            object_id=str(report.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "report_id": str(report.id),
                "day_id": str(report.day_id),
                "status": report.status,
            },
        )

    @classmethod
    def log_report_rejected_empty(cls, request, report) -> None:
        log_event(
            action=AuditEvents.REPORT_REJECTED_EMPTY,
            actor=request.user,
            object_type="onboarding_report",
            object_id=str(report.id),
            level="warning",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "report_id": str(report.id),
                "day_id": str(report.day_id),
                "status": report.status,
            },
        )

    @classmethod
    def log_report_deadline_blocked(cls, request, day) -> None:
        log_event(
            action=AuditEvents.REPORT_DEADLINE_BLOCKED,
            actor=request.user,
            object_type="onboarding_day",
            object_id=str(day.id),
            level="warning",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "day_id": str(day.id),
                "day_number": day.day_number,
            },
        )

    @classmethod
    def log_report_edit_conflict(cls, request, report) -> None:
        log_event(
            action=AuditEvents.REPORT_EDIT_CONFLICT,
            actor=request.user,
            object_type="onboarding_report",
            object_id=str(report.id),
            level="warning",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "report_id": str(report.id),
                "day_id": str(report.day_id),
                "status": report.status,
            },
        )

    @classmethod
    def log_review_status_changed(cls, request, report, from_status: str, to_status: str, has_comment: bool) -> None:
        log_event(
            action=AuditEvents.REPORT_REVIEW_STATUS_CHANGED,
            actor=request.user,
            object_type="onboarding_report",
            object_id=str(report.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "report_id": str(report.id),
                "from_status": from_status,
                "to_status": to_status,
                "has_comment": has_comment,
            },
        )
