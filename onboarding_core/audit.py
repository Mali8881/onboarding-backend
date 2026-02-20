from __future__ import annotations

from typing import Any, Optional

from apps.audit import AuditEvents, log_event


class OnboardingAuditService:
    @staticmethod
    def _ip(request) -> Optional[str]:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @classmethod
    def log_day_completed(cls, request, day, completed_at, *, idempotent: bool = False) -> None:
        action = (
            AuditEvents.ONBOARDING_DAY_COMPLETED_IDEMPOTENT
            if idempotent
            else AuditEvents.ONBOARDING_DAY_COMPLETED
        )
        field_name = "existing_completed_at" if idempotent else "completed_at"
        log_event(
            action=action,
            actor=request.user,
            object_type="onboarding_day",
            object_id=str(day.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "user_id": request.user.id,
                "day_number": day.day_number,
                field_name: completed_at.isoformat() if completed_at else None,
            },
        )

    @classmethod
    def log_overview_viewed(cls, request, *, total_days: int, completed_days: int, progress_percent: int) -> None:
        log_event(
            action=AuditEvents.ONBOARDING_OVERVIEW_VIEWED,
            actor=request.user,
            object_type="onboarding",
            object_id="",
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "user_id": request.user.id,
                "total_days": total_days,
                "completed_days": completed_days,
                "progress_percent": progress_percent,
            },
        )

    @classmethod
    def log_day_created(cls, request, day) -> None:
        log_event(
            action=AuditEvents.ONBOARDING_DAY_CREATED,
            actor=request.user,
            object_type="onboarding_day",
            object_id=str(day.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "day_number": day.day_number,
                "title": day.title,
                "is_active": day.is_active,
            },
        )

    @classmethod
    def log_day_updated(cls, request, day, changed_fields: list[str]) -> None:
        log_event(
            action=AuditEvents.ONBOARDING_DAY_UPDATED,
            actor=request.user,
            object_type="onboarding_day",
            object_id=str(day.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "changed_fields": changed_fields,
            },
        )

    @classmethod
    def log_day_deleted(cls, request, day) -> None:
        log_event(
            action=AuditEvents.ONBOARDING_DAY_DELETED,
            actor=request.user,
            object_type="onboarding_day",
            object_id=str(day.id),
            level="warning",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "day_number": day.day_number,
                "title": day.title,
            },
        )

    @classmethod
    def log_material_created(cls, request, material) -> None:
        log_event(
            action=AuditEvents.ONBOARDING_MATERIAL_CREATED,
            actor=request.user,
            object_type="onboarding_material",
            object_id=str(material.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "day_id": str(material.day_id),
                "type": material.type,
                "position": material.position,
            },
        )

    @classmethod
    def log_material_updated(cls, request, material, changed_fields: list[str]) -> None:
        log_event(
            action=AuditEvents.ONBOARDING_MATERIAL_UPDATED,
            actor=request.user,
            object_type="onboarding_material",
            object_id=str(material.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "day_id": str(material.day_id),
                "changed_fields": changed_fields,
            },
        )

    @classmethod
    def log_material_deleted(cls, request, material) -> None:
        log_event(
            action=AuditEvents.ONBOARDING_MATERIAL_DELETED,
            actor=request.user,
            object_type="onboarding_material",
            object_id=str(material.id),
            level="warning",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "day_id": str(material.day_id),
                "type": material.type,
            },
        )

    @classmethod
    def log_progress_viewed_admin(cls, request, filters: dict[str, Any]) -> None:
        log_event(
            action=AuditEvents.ONBOARDING_PROGRESS_VIEWED_ADMIN,
            actor=request.user,
            object_type="onboarding_progress",
            object_id="",
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "filters": filters,
            },
        )
