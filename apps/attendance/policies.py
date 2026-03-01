from __future__ import annotations

from datetime import date

from accounts.access_policy import AccessPolicy
from accounts.models import Role


class AttendancePolicy:
    @staticmethod
    def is_admin_like(user) -> bool:
        return AccessPolicy.is_admin(user) or AccessPolicy.is_main_admin(user) or AccessPolicy.is_super_admin(user)

    @classmethod
    def can_view_team(cls, actor) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if cls.is_admin_like(actor):
            return True
        return AccessPolicy.is_teamlead(actor)

    @classmethod
    def can_manage_work_calendar(cls, actor) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        return cls.is_admin_like(actor)

    @staticmethod
    def _role_name(user) -> str | None:
        if not user or not getattr(user, "role_id", None):
            return None
        return user.role.name

    @classmethod
    def is_trackable_user(cls, user) -> bool:
        role_name = cls._role_name(user)
        return role_name in {
            Role.Name.DEPARTMENT_HEAD,
            Role.Name.ADMIN,
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
        actor_role = cls._role_name(actor)
        target_role = cls._role_name(target_user)
        if actor_role == Role.Name.SUPER_ADMIN:
            return target_role in {
                Role.Name.DEPARTMENT_HEAD,
                Role.Name.ADMIN,
                Role.Name.TEAMLEAD,
                Role.Name.EMPLOYEE,
                Role.Name.INTERN,
            }
        if actor_role == Role.Name.ADMIN:
            return target_role in {Role.Name.DEPARTMENT_HEAD, Role.Name.TEAMLEAD, Role.Name.EMPLOYEE, Role.Name.INTERN}
        if actor_role == Role.Name.DEPARTMENT_HEAD:
            return target_role in {Role.Name.TEAMLEAD, Role.Name.EMPLOYEE, Role.Name.INTERN}
        if actor_role == Role.Name.TEAMLEAD:
            return target_user.manager_id == actor.id and target_role in {Role.Name.EMPLOYEE, Role.Name.INTERN}
        if actor.id == target_user.id:
            return actor_role in {Role.Name.TEAMLEAD, Role.Name.EMPLOYEE, Role.Name.INTERN}
        if cls.is_admin_like(actor):
            return True
        return target_user.manager_id == actor.id

    @classmethod
    def can_edit_mark(cls, actor, target_user, mark_date: date) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if mark_date > date.today():
            return False
        if not cls.is_trackable_user(target_user):
            return False
        actor_role = cls._role_name(actor)
        target_role = cls._role_name(target_user)
        if actor.id == target_user.id:
            return actor_role in {
                Role.Name.DEPARTMENT_HEAD,
                Role.Name.ADMIN,
                Role.Name.TEAMLEAD,
                Role.Name.EMPLOYEE,
                Role.Name.INTERN,
            }
        if actor_role == Role.Name.SUPER_ADMIN:
            return target_role in {
                Role.Name.DEPARTMENT_HEAD,
                Role.Name.ADMIN,
                Role.Name.TEAMLEAD,
                Role.Name.EMPLOYEE,
                Role.Name.INTERN,
            }
        if actor_role == Role.Name.ADMIN:
            return target_role in {Role.Name.DEPARTMENT_HEAD, Role.Name.TEAMLEAD, Role.Name.EMPLOYEE, Role.Name.INTERN}
        if actor_role == Role.Name.DEPARTMENT_HEAD:
            return target_role in {Role.Name.TEAMLEAD, Role.Name.EMPLOYEE, Role.Name.INTERN}
        if actor_role == Role.Name.TEAMLEAD:
            return target_user.manager_id == actor.id and target_role in {Role.Name.EMPLOYEE, Role.Name.INTERN}
        if cls.is_admin_like(actor):
            return True
        return target_user.manager_id == actor.id

    @classmethod
    def can_view_user_marks(cls, actor, target_user) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if not cls.is_trackable_user(target_user):
            return False
        if actor.id == target_user.id:
            return True
        actor_role = cls._role_name(actor)
        target_role = cls._role_name(target_user)
        if actor_role == Role.Name.SUPER_ADMIN:
            return target_role in {
                Role.Name.DEPARTMENT_HEAD,
                Role.Name.ADMIN,
                Role.Name.TEAMLEAD,
                Role.Name.EMPLOYEE,
                Role.Name.INTERN,
            }
        if actor_role == Role.Name.ADMIN:
            return target_role in {Role.Name.DEPARTMENT_HEAD, Role.Name.TEAMLEAD, Role.Name.EMPLOYEE, Role.Name.INTERN}
        if actor_role == Role.Name.DEPARTMENT_HEAD:
            return target_role in {Role.Name.TEAMLEAD, Role.Name.EMPLOYEE, Role.Name.INTERN}
        if actor_role == Role.Name.TEAMLEAD:
            return target_user.manager_id == actor.id and target_role in {Role.Name.EMPLOYEE, Role.Name.INTERN}
        if cls.is_admin_like(actor):
            return True
        return target_user.manager_id == actor.id
