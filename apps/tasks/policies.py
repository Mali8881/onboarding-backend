from __future__ import annotations

from accounts.access_policy import AccessPolicy


class TaskPolicy:
    @staticmethod
    def is_admin_like(user) -> bool:
        return AccessPolicy.is_admin_like(user)

    @classmethod
    def can_manage_team(cls, actor) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if cls.is_admin_like(actor):
            return True
        return actor.team_members.exists()

    @classmethod
    def can_assign_task(cls, actor, assignee) -> bool:
        if cls.is_admin_like(actor):
            return True
        return assignee.manager_id == actor.id

    @classmethod
    def can_view_task(cls, actor, task) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if cls.is_admin_like(actor):
            return True
        if task.assignee_id == actor.id or task.reporter_id == actor.id:
            return True
        return task.assignee.manager_id == actor.id

    @classmethod
    def can_edit_task(cls, actor, task) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if cls.is_admin_like(actor):
            return True
        if task.reporter_id == actor.id:
            return True
        return task.assignee.manager_id == actor.id
