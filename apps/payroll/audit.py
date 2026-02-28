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
    def log_hourly_rate_changed(cls, request, history) -> None:
        log_event(
            action=AuditEvents.HOURLY_RATE_CHANGED,
            actor=request.user,
            object_type="hourly_rate_history",
            object_id=str(history.id),
            category="content",
            ip_address=cls._ip(request),
            metadata={"user_id": history.user_id, "rate": str(history.rate), "start_date": history.start_date.isoformat()},
        )

    @classmethod
    def log_period_generated(cls, request, year: int, month: int, created: int, updated: int) -> None:
        log_event(
            action=AuditEvents.PAYROLL_PERIOD_GENERATED,
            actor=request.user,
            object_type="payroll_month",
            object_id=f"{year}-{month:02d}",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "year": year,
                "month": month,
                "entries_created": created,
                "entries_updated": updated,
            },
        )

    @classmethod
    def log_period_status_changed(cls, request, record, previous_status: str) -> None:
        log_event(
            action=AuditEvents.PAYROLL_PERIOD_STATUS_CHANGED,
            actor=request.user,
            object_type="payroll_record",
            object_id=str(record.id),
            category="content",
            ip_address=cls._ip(request),
            metadata={"from": previous_status, "to": record.status, "user_id": record.user_id, "month": record.month.isoformat()},
        )
