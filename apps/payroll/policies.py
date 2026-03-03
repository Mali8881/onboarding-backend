from __future__ import annotations

from accounts.access_policy import AccessPolicy
from accounts.models import Role


class PayrollPolicy:
    LEGACY_DEPARTMENT_HEAD_NAMES = {"DEPARTMENT_HEAD", "DEPARTMENTHEAD"}

    @staticmethod
    def _role_name(user) -> str | None:
        if not user or not getattr(user, "role_id", None):
            return None
        return str(user.role.name).upper()

    @classmethod
    def _is_department_head(cls, user) -> bool:
        return cls._role_name(user) in cls.LEGACY_DEPARTMENT_HEAD_NAMES

    @staticmethod
    def is_salary_enabled_user(user) -> bool:
        role_name = PayrollPolicy._role_name(user)
        return role_name in {
            Role.Name.SUPER_ADMIN,
            Role.Name.ADMINISTRATOR,
            Role.Name.ADMIN,
            Role.Name.EMPLOYEE,
        } or role_name in PayrollPolicy.LEGACY_DEPARTMENT_HEAD_NAMES

    @staticmethod
    def can_manage_payroll(user) -> bool:
        return bool(
            user
            and user.is_authenticated
            and (AccessPolicy.is_super_admin(user) or AccessPolicy.is_administrator(user))
        )

    @staticmethod
    def can_view_payroll(user) -> bool:
        return bool(
            user
            and user.is_authenticated
            and (
                AccessPolicy.is_super_admin(user)
                or AccessPolicy.is_administrator(user)
                or AccessPolicy.is_admin(user)
                or PayrollPolicy._is_department_head(user)
            )
        )

    @staticmethod
    def can_view_own(user) -> bool:
        return bool(user and user.is_authenticated and PayrollPolicy.is_salary_enabled_user(user))

    @staticmethod
    def can_manage_hourly_rates(user) -> bool:
        return PayrollPolicy.can_manage_payroll(user)

    @staticmethod
    def can_edit_compensation(user) -> bool:
        return bool(
            user
            and user.is_authenticated
            and (
                AccessPolicy.is_super_admin(user)
                or AccessPolicy.is_administrator(user)
                or AccessPolicy.is_admin(user)
                or PayrollPolicy._is_department_head(user)
            )
        )

    @staticmethod
    def can_edit_compensation_for_user(actor, target_user) -> bool:
        return PayrollPolicy.compensation_edit_denial_reason(actor, target_user) is None

    @staticmethod
    def compensation_edit_denial_reason(actor, target_user) -> str | None:
        if not PayrollPolicy.can_edit_compensation(actor):
            return "Insufficient permissions to edit compensations."
        if not PayrollPolicy.is_salary_enabled_user(target_user):
            return "Payroll is not enabled for target user's role."
        if actor.id == target_user.id:
            return "You cannot edit your own salary settings."
        if AccessPolicy.is_super_admin(actor) or AccessPolicy.is_administrator(actor):
            return None
        if not (AccessPolicy.is_admin(actor) or PayrollPolicy._is_department_head(actor)):
            return "Insufficient permissions to edit selected employee."
        if not getattr(actor, "department_id", None) or not getattr(target_user, "department_id", None):
            return "Department is not set for actor or target user."
        if actor.department_id != target_user.department_id:
            return "You can edit only users from your department."
        target_role = str(getattr(getattr(target_user, "role", None), "name", "")).upper()
        if target_role != Role.Name.EMPLOYEE:
            return "Department admin can edit compensation only for EMPLOYEE role."
        return None
