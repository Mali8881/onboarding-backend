from __future__ import annotations

from accounts.access_policy import AccessPolicy


class TaskPolicy:
    @staticmethod
    def is_admin_like(user) -> bool:
        return AccessPolicy.is_admin(user) or AccessPolicy.is_main_admin(user) or AccessPolicy.is_super_admin(user)

    @staticmethod
    def is_department_admin(user) -> bool:
        return AccessPolicy.is_admin(user) and not AccessPolicy.is_main_admin(user) and not AccessPolicy.is_super_admin(user)

    @classmethod
    def _in_admin_scope(cls, actor, assignee) -> bool:
        if AccessPolicy.is_super_admin(actor) or AccessPolicy.is_main_admin(actor):
            return True
        if cls.is_department_admin(actor):
            return bool(actor.department_id and assignee.department_id == actor.department_id)
        return False

    @classmethod
    def can_manage_team(cls, actor) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if cls.is_admin_like(actor):
            return True
        return AccessPolicy.is_teamlead(actor)

    @classmethod
    def can_assign_task(cls, actor, assignee) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        # Any authenticated user can create a task for themselves.
        if actor.id == assignee.id:
            return True
        if AccessPolicy.is_super_admin(actor) or AccessPolicy.is_main_admin(actor):
            return True
        if cls.is_department_admin(actor):
            return cls._in_admin_scope(actor, assignee)
        return AccessPolicy.is_teamlead(actor) and assignee.manager_id == actor.id

    @classmethod
    def can_view_task(cls, actor, task) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if AccessPolicy.is_super_admin(actor) or AccessPolicy.is_main_admin(actor):
            return True
        if cls.is_department_admin(actor):
            return cls._in_admin_scope(actor, task.assignee)
        if task.assignee_id == actor.id or task.reporter_id == actor.id:
            return True
        return AccessPolicy.is_teamlead(actor) and task.assignee.manager_id == actor.id

    @classmethod
    def can_edit_task(cls, actor, task) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if task.assignee_id == actor.id:
            return True
        if AccessPolicy.is_super_admin(actor) or AccessPolicy.is_main_admin(actor):
            return True
        if cls.is_department_admin(actor):
            return cls._in_admin_scope(actor, task.assignee)
        if task.reporter_id == actor.id:
            return True
        return AccessPolicy.is_teamlead(actor) and task.assignee.manager_id == actor.id

