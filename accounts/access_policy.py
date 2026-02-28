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
    def is_administrator(cls, user) -> bool:
        return cls._has_role(user) and user.role.name == Role.Name.ADMINISTRATOR

    @classmethod
    def is_admin(cls, user) -> bool:
        return cls._has_role(user) and user.role.name == Role.Name.ADMIN

    @classmethod
    def is_admin_like(cls, user) -> bool:
        return cls.is_super_admin(user) or cls.is_administrator(user) or cls.is_admin(user)

    @classmethod
    def is_employee(cls, user) -> bool:
        return cls._has_role(user) and user.role.name == Role.Name.EMPLOYEE

    @classmethod
    def is_teamlead(cls, user) -> bool:
        return cls._has_role(user) and user.role.name == Role.Name.TEAMLEAD

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
        if cls.is_administrator(actor) or cls.is_admin(actor):
            return target.role.name in {
                Role.Name.ADMIN,
                Role.Name.ADMINISTRATOR,
                Role.Name.TEAMLEAD,
                Role.Name.EMPLOYEE,
                Role.Name.INTERN,
            }
        if cls.is_teamlead(actor):
            return target.manager_id == actor.id
        return False

    @classmethod
    def can_manage_user(cls, actor, target) -> bool:
        if not cls._has_role(actor):
            return False
        if cls.is_super_admin(actor):
            return target.role.name != Role.Name.SUPER_ADMIN
        if cls.is_administrator(actor) or cls.is_admin(actor):
            return target.role.name in {Role.Name.TEAMLEAD, Role.Name.INTERN, Role.Name.EMPLOYEE}
        if cls.is_teamlead(actor):
            return target.manager_id == actor.id and target.role.name in {Role.Name.INTERN, Role.Name.EMPLOYEE}
        return False

    @classmethod
    def can_view_team(cls, actor) -> bool:
        if not cls._has_role(actor):
            return False
        if cls.is_admin_like(actor):
            return True
        return cls.is_teamlead(actor)

    @classmethod
    def can_manage_org_reference(cls, actor) -> bool:
        """Department/Position CRUD."""
        return cls.is_admin_like(actor)

    @classmethod
    def can_access_admin_panel(cls, user) -> bool:
        return bool(user and user.is_authenticated and cls.is_admin_like(user))
