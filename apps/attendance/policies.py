from __future__ import annotations

from datetime import date

from apps.accounts.access_policy import AccessPolicy
from apps.accounts.models import Role


class AttendancePolicy:

    @classmethod
    def can_view_team(cls, actor) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        return AccessPolicy.can_view_team_attendance(actor)

    @classmethod
    def can_manage_work_calendar(cls, actor) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        return AccessPolicy.can_manage_work_calendar(actor)

    @staticmethod
    def _role_name(user) -> str | None:
        if not user or not getattr(user, "role_id", None):
            return None
        return user.role.name

    @classmethod
    def is_trackable_user(cls, user) -> bool:
        role_name = cls._role_name(user)
        return role_name in {
            Role.Name.ADMIN,
            Role.Name.ADMINISTRATOR,
            Role.Name.TEAMLEAD,
            Role.Name.EMPLOYEE,
            Role.Name.INTERN,
        }

    @classmethod
    def can_delete_mark(cls, actor, target_user) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if not cls.is_trackable_user(target_user):
            return False
        if AccessPolicy.is_super_admin(actor):
            return True
        if AccessPolicy.can_manage_attendance(actor):
            return True
        if AccessPolicy.is_teamlead(actor):
            return target_user.manager_id == actor.id and cls._role_name(target_user) in {
                Role.Name.EMPLOYEE,
                Role.Name.INTERN,
            }
        return False

    @classmethod
    def can_edit_mark(cls, actor, target_user, mark_date: date) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if mark_date > date.today():
            return False
        if actor.id == target_user.id:
            return AccessPolicy.has_permission(actor, "attendance.mark_own")
        if not cls.is_trackable_user(target_user):
            return False
        if AccessPolicy.can_manage_attendance(actor):
            return True
        if AccessPolicy.is_teamlead(actor):
            return target_user.manager_id == actor.id and cls._role_name(target_user) in {
                Role.Name.EMPLOYEE,
                Role.Name.INTERN,
            }
        return False

    @classmethod
    def can_view_user_marks(cls, actor, target_user) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if actor.id == target_user.id:
            return AccessPolicy.has_permission(actor, "attendance.view_own")
        if not cls.is_trackable_user(target_user):
            return False
        if AccessPolicy.can_view_team_attendance(actor):
            return True
        if AccessPolicy.is_teamlead(actor):
            return target_user.manager_id == actor.id
        return False
