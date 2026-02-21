from __future__ import annotations

from typing import Optional

from apps.audit import AuditEvents, log_event


class TasksAuditService:
    @staticmethod
    def _ip(request) -> Optional[str]:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @classmethod
    def log_task_created(cls, request, task) -> None:
        log_event(
            action=AuditEvents.TASK_CREATED,
            actor=request.user,
            object_type="task",
            object_id=str(task.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "assignee_id": task.assignee_id,
                "board_id": task.board_id,
                "column_id": task.column_id,
            },
        )

    @classmethod
    def log_task_updated(cls, request, task, changed_fields: list[str]) -> None:
        log_event(
            action=AuditEvents.TASK_UPDATED,
            actor=request.user,
            object_type="task",
            object_id=str(task.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "changed_fields": changed_fields,
            },
        )

    @classmethod
    def log_task_moved(cls, request, task, from_column_id: int, to_column_id: int) -> None:
        log_event(
            action=AuditEvents.TASK_MOVED,
            actor=request.user,
            object_type="task",
            object_id=str(task.id),
            level="info",
            category="content",
            ip_address=cls._ip(request),
            metadata={
                "actor_id": request.user.id,
                "from_column_id": from_column_id,
                "to_column_id": to_column_id,
            },
        )

