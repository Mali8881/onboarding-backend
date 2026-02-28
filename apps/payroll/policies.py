from __future__ import annotations

from accounts.access_policy import AccessPolicy
from accounts.models import Role


class PayrollPolicy:
    @staticmethod
    def _role_name(user) -> str | None:
        if not user or not getattr(user, "role_id", None):
            return None
        return user.role.name

    @staticmethod
    def is_salary_enabled_user(user) -> bool:
        role_name = PayrollPolicy._role_name(user)
        return role_name in {
            Role.Name.SUPER_ADMIN,
            Role.Name.ADMINISTRATOR,
            Role.Name.ADMIN,
            Role.Name.EMPLOYEE,
        }

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
            )
        )

    @staticmethod
    def can_edit_compensation_for_user(actor, target_user) -> bool:
        if not PayrollPolicy.can_edit_compensation(actor):
            return False
        if not PayrollPolicy.is_salary_enabled_user(target_user):
            return False
        if actor.id == target_user.id:
            return False
        if AccessPolicy.is_super_admin(actor) or AccessPolicy.is_administrator(actor):
            return True
        if not AccessPolicy.is_admin(actor):
            return False
        if not getattr(actor, "department_id", None) or not getattr(target_user, "department_id", None):
            return False
        if actor.department_id != target_user.department_id:
            return False
        target_role = getattr(getattr(target_user, "role", None), "name", None)
        return target_role == Role.Name.EMPLOYEE
