from __future__ import annotations

from typing import Iterable

from .models import Role


class AccessPolicy:
    """Centralized access checks for role/permission/object rules."""

    @staticmethod
    def _has_role(user) -> bool:
        return bool(user and user.is_authenticated and getattr(user, "role", None))

    @classmethod
    def role_level(cls, user) -> int:
        if not cls._has_role(user):
            return 0
        return int(user.role.level)

    @classmethod
    def has_permission(cls, user, codename: str) -> bool:
        if not cls._has_role(user):
            return False
        return user.role.permissions.filter(codename=codename).exists()

    @classmethod
    def has_any_permission(cls, user, codenames: Iterable[str]) -> bool:
        if not cls._has_role(user):
            return False
        return user.role.permissions.filter(codename__in=list(codenames)).exists()

    @classmethod
    def has_all_permissions(cls, user, codenames: Iterable[str]) -> bool:
        if not cls._has_role(user):
            return False
        current = set(user.role.permissions.values_list("codename", flat=True))
        return set(codenames).issubset(current)

    @classmethod
    def is_super_admin(cls, user) -> bool:
        return cls._has_role(user) and user.role.name == Role.Name.SUPER_ADMIN

    @classmethod
    def is_admin(cls, user) -> bool:
        return cls._has_role(user) and user.role.name == Role.Name.ADMIN

    @classmethod
    def is_employee(cls, user) -> bool:
        return cls._has_role(user) and user.role.name == Role.Name.EMPLOYEE

    @classmethod
    def is_intern(cls, user) -> bool:
        return cls._has_role(user) and user.role.name == Role.Name.INTERN

    @classmethod
    def can_view_user(cls, actor, target) -> bool:
        if not cls._has_role(actor):
            return False
        if actor.pk == target.pk:
            return True
        if cls.is_super_admin(actor):
            return True
        if cls.is_admin(actor):
            return target.role.name in {Role.Name.INTERN, Role.Name.EMPLOYEE}
        if actor.role.name == Role.Name.EMPLOYEE:
            return target.manager_id == actor.id
        return False

    @classmethod
    def can_manage_user(cls, actor, target) -> bool:
        if not cls._has_role(actor):
            return False
        if cls.is_super_admin(actor):
            return True
        if cls.is_admin(actor):
            return target.role.name in {Role.Name.INTERN, Role.Name.EMPLOYEE}
        return False

    @classmethod
    def can_access_admin_panel(cls, user) -> bool:
        return bool(user and user.is_authenticated and user.is_staff)
