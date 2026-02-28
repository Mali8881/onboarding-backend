from rest_framework.permissions import BasePermission

from .policies import PayrollPolicy


class IsPayrollSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return PayrollPolicy.can_manage_payroll(request.user)


class IsPayrollViewer(BasePermission):
    def has_permission(self, request, view):
        return PayrollPolicy.can_view_payroll(request.user)


class IsPayrollCompensationEditor(BasePermission):
    def has_permission(self, request, view):
        return PayrollPolicy.can_edit_compensation(request.user)


class IsPayrollAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return PayrollPolicy.can_view_own(request.user)
