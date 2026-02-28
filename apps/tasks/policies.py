from __future__ import annotations

from accounts.access_policy import AccessPolicy


class TaskPolicy:
    @staticmethod
    def is_admin_like(user) -> bool:
        return AccessPolicy.is_admin(user) or AccessPolicy.is_super_admin(user)

    @classmethod
    def can_manage_team(cls, actor) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if cls.is_admin_like(actor):
            return True
        return AccessPolicy.is_teamlead(actor)

    @classmethod
    def can_assign_task(cls, actor, assignee) -> bool:
        if cls.is_admin_like(actor):
            return True
        return AccessPolicy.is_teamlead(actor) and assignee.manager_id == actor.id

    @classmethod
    def can_view_task(cls, actor, task) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if cls.is_admin_like(actor):
            return True
        if task.assignee_id == actor.id or task.reporter_id == actor.id:
            return True
        return AccessPolicy.is_teamlead(actor) and task.assignee.manager_id == actor.id

    @classmethod
    def can_edit_task(cls, actor, task) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if cls.is_admin_like(actor):
            return True
        if task.reporter_id == actor.id:
            return True
        return AccessPolicy.is_teamlead(actor) and task.assignee.manager_id == actor.id

