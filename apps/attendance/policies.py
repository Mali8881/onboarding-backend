from __future__ import annotations

from datetime import date

from accounts.access_policy import AccessPolicy


class AttendancePolicy:
    @staticmethod
    def is_admin_like(user) -> bool:
        return AccessPolicy.is_admin(user) or AccessPolicy.is_super_admin(user)

    @classmethod
    def can_view_team(cls, actor) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if cls.is_admin_like(actor):
            return True
        return actor.team_members.exists()

    @classmethod
    def can_edit_mark(cls, actor, target_user, mark_date: date) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if mark_date > date.today():
            return False
        if actor.id == target_user.id:
            return True
        if cls.is_admin_like(actor):
            return True
        return target_user.manager_id == actor.id

    @classmethod
    def can_view_user_marks(cls, actor, target_user) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if actor.id == target_user.id:
            return True
        if cls.is_admin_like(actor):
            return True
        return target_user.manager_id == actor.id

