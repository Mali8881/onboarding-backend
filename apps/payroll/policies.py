from __future__ import annotations

from accounts.access_policy import AccessPolicy


class PayrollPolicy:

    @staticmethod
    def can_manage_payroll(user) -> bool:
        return bool(user and user.is_authenticated and AccessPolicy.can_manage_payroll(user))

    @staticmethod
    def can_view_payroll(user) -> bool:
        """Full payroll view (all users). Admin/Administrator/SuperAdmin."""
        return PayrollPolicy.can_manage_payroll(user)

    @staticmethod
    def is_salary_enabled_user(user) -> bool:
        """User can see their own payroll record."""
        return bool(user and user.is_authenticated and AccessPolicy.can_view_own_payroll(user))

    @staticmethod
    def can_view_own(user) -> bool:
        return PayrollPolicy.is_salary_enabled_user(user)

    @staticmethod
    def can_manage_hourly_rates(user) -> bool:
        return PayrollPolicy.can_manage_payroll(user)

    @staticmethod
    def can_edit_compensation(user) -> bool:
        return PayrollPolicy.can_manage_payroll(user)

    @staticmethod
    def can_edit_compensation_for_user(actor, target_user) -> bool:
        return PayrollPolicy.compensation_edit_denial_reason(actor, target_user) is None

    @staticmethod
    def compensation_edit_denial_reason(actor, target_user) -> str | None:
        if not PayrollPolicy.can_edit_compensation(actor):
            return "Insufficient permissions to edit compensations."
        if actor.id == target_user.id:
            return "You cannot edit your own salary settings."
        if AccessPolicy.is_super_admin(actor) or AccessPolicy.is_administrator(actor):
            return None
        if AccessPolicy.is_admin(actor):
            if not getattr(actor, "department_id", None) or not getattr(target_user, "department_id", None):
                return "Department is not set for actor or target user."
            if actor.department_id != target_user.department_id:
                return "You can edit only users from your department."
        return None
