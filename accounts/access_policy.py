from __future__ import annotations

from typing import Iterable

from .models import Role


class AccessPolicy:
    """Centralized access checks for role/permission/object rules."""

    LEGACY_SYSTEM_ADMIN_NAMES = {"SYSTEMADMIN", "SYSTEM_ADMIN", "SYSTEM_ADMINISTRATOR"}
    LEGACY_DEPARTMENT_HEAD_NAMES = {"DEPARTMENT_HEAD", "DEPARTMENTHEAD", "DEPARTMENT HEAD"}

    @staticmethod
    def _has_role(user) -> bool:
        return bool(user and user.is_authenticated and getattr(user, "role", None))

    @classmethod
    def _role_name(cls, user) -> str | None:
        if not cls._has_role(user):
            return None
        return str(user.role.name).upper()

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
        return cls._role_name(user) == Role.Name.SUPER_ADMIN

    @classmethod
    def is_administrator(cls, user) -> bool:
        role_name = cls._role_name(user)
        if not role_name:
            return False
        return role_name == Role.Name.ADMINISTRATOR or role_name in cls.LEGACY_SYSTEM_ADMIN_NAMES

    @classmethod
    def is_admin(cls, user) -> bool:
        role_name = cls._role_name(user)
        if not role_name:
            return False
        return role_name == Role.Name.ADMIN or role_name in cls.LEGACY_DEPARTMENT_HEAD_NAMES

    @classmethod
    def is_department_head(cls, user) -> bool:
        role_name = cls._role_name(user)
        return bool(role_name and role_name in cls.LEGACY_DEPARTMENT_HEAD_NAMES)

    @classmethod
    def is_admin_like(cls, user) -> bool:
        return cls.is_super_admin(user) or cls.is_administrator(user) or cls.is_admin(user)

    @classmethod
    def admin_recipient_role_names(cls) -> set[str]:
        """Role names that should receive admin-targeted notifications."""
        return {
            Role.Name.SUPER_ADMIN,
            Role.Name.ADMINISTRATOR,
            Role.Name.ADMIN,
            *cls.LEGACY_SYSTEM_ADMIN_NAMES,
            *cls.LEGACY_DEPARTMENT_HEAD_NAMES,
        }

    @classmethod
    def is_main_admin(cls, user) -> bool:
        """Alias for is_administrator() kept for backward compatibility."""
        return cls.is_administrator(user)

    @classmethod
    def is_employee(cls, user) -> bool:
        return cls._has_role(user) and user.role.name == Role.Name.EMPLOYEE

    @classmethod
    def is_teamlead(cls, user) -> bool:
        return cls._has_role(user) and user.role.name == Role.Name.TEAMLEAD

    @classmethod
    def is_intern(cls, user) -> bool:
        return cls._has_role(user) and user.role.name == Role.Name.INTERN

    # ------------------------------------------------------------------
    # Permission-based checks (RBAC-driven, preferred over role-name checks)
    # ------------------------------------------------------------------

    @classmethod
    def can_manage_tasks(cls, user) -> bool:
        return cls.has_permission(user, "tasks.manage_team")

    @classmethod
    def can_manage_attendance(cls, user) -> bool:
        return cls.has_permission(user, "attendance.manage")

    @classmethod
    def can_view_team_attendance(cls, user) -> bool:
        return cls.has_permission(user, "attendance.view_team")

    @classmethod
    def can_approve_attendance(cls, user) -> bool:
        return cls.has_permission(user, "attendance.approve")

    @classmethod
    def can_manage_work_calendar(cls, user) -> bool:
        return cls.has_permission(user, "attendance.calendar")

    @classmethod
    def can_manage_payroll(cls, user) -> bool:
        if cls.has_permission(user, "payroll.manage"):
            return True
        # Backward-compatible fallback for deployments where payroll perms are not seeded yet.
        return cls.is_admin_like(user)

    @classmethod
    def can_view_own_payroll(cls, user) -> bool:
        if cls.has_permission(user, "payroll.view_own"):
            return True
        if not cls._has_role(user):
            return False
        role_name = cls._role_name(user)
        return role_name in {
            Role.Name.SUPER_ADMIN,
            Role.Name.ADMINISTRATOR,
            Role.Name.ADMIN,
            Role.Name.EMPLOYEE,
        } or cls.is_department_head(user)

    @classmethod
    def can_manage_bpm_templates(cls, user) -> bool:
        return cls.has_permission(user, "bpm.manage_templates")

    @classmethod
    def can_manage_kb(cls, user) -> bool:
        return cls.has_permission(user, "kb.delete")

    @classmethod
    def can_view_team_metrics(cls, user) -> bool:
        return cls.has_permission(user, "metrics.view_team")

    @classmethod
    def can_manage_org(cls, user) -> bool:
        return cls.has_permission(user, "org.manage")

    @classmethod
    def can_view_audit_log(cls, user) -> bool:
        return cls.has_permission(user, "audit.view")

    # ------------------------------------------------------------------
    # Object-level checks (actor vs. specific target user)
    # ------------------------------------------------------------------

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
            # Admin manages everyone except SuperAdmin
            return target.role.name != Role.Name.SUPER_ADMIN
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
        return cls.can_manage_org(actor)

    @classmethod
    def can_access_admin_panel(cls, user) -> bool:
        return bool(user and user.is_authenticated and cls.is_admin_like(user))
