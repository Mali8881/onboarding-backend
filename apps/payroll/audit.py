from __future__ import annotations

from typing import Optional

from apps.audit import AuditEvents, log_event


class PayrollAuditService:
    @staticmethod
    def _ip(request) -> Optional[str]:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @classmethod
    def log_salary_profile_created(cls, request, profile) -> None:
        log_event(
            action=AuditEvents.SALARY_PROFILE_CREATED,
            actor=request.user,
            object_type="salary_profile",
            object_id=str(profile.id),
            category="content",
            ip_address=cls._ip(request),
            metadata={"user_id": profile.user_id},
        )

    @classmethod
    def log_salary_profile_updated(cls, request, profile, changed_fields: list[str]) -> None:
        log_event(
            action=AuditEvents.SALARY_PROFILE_UPDATED,
            actor=request.user,
            object_type="salary_profile",
            object_id=str(profile.id),
            category="content",
            ip_address=cls._ip(request),
            metadata={"user_id": profile.user_id, "changed_fields": changed_fields},
        )

    @classmethod
    def log_period_generated(cls, request, period, created: int, updated: int) -> None:
        log_event(
            action=AuditEvents.PAYROLL_PERIOD_GENERATED,
            actor=request.user,
            object_type="payroll_period",
            object_id=str(period.id),
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "year": period.year,
                "month": period.month,
                "entries_created": created,
                "entries_updated": updated,
            },
        )

    @classmethod
    def log_period_status_changed(cls, request, period, previous_status: str) -> None:
        log_event(
            action=AuditEvents.PAYROLL_PERIOD_STATUS_CHANGED,
            actor=request.user,
            object_type="payroll_period",
            object_id=str(period.id),
            category="content",
            ip_address=cls._ip(request),
            metadata={"from": previous_status, "to": period.status},
        )

