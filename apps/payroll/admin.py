from django.contrib import admin
from django.contrib.auth import get_user_model

from accounts.models import Role
from .policies import PayrollPolicy

from .models import PayrollCompensation

User = get_user_model()


class PayrollViewAdminMixin:
    def _can_view(self, request) -> bool:
        return PayrollPolicy.can_view_payroll(request.user)

    def has_module_permission(self, request):
        return self._can_view(request)

    def has_view_permission(self, request, obj=None):
        return self._can_view(request)


class PayrollManageAdminMixin(PayrollViewAdminMixin):
    def _can_manage(self, request) -> bool:
        return PayrollPolicy.can_manage_payroll(request.user)

    def has_add_permission(self, request):
        return self._can_manage(request)

    def has_change_permission(self, request, obj=None):
        return self._can_manage(request)

    def has_delete_permission(self, request, obj=None):
        return self._can_manage(request)


@admin.register(PayrollCompensation)
class PayrollCompensationAdmin(PayrollViewAdminMixin, admin.ModelAdmin):
    list_display = ("user", "pay_type", "hourly_rate", "minute_rate", "fixed_salary", "updated_at")
    list_filter = ("pay_type",)
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return PayrollPolicy.can_manage_payroll(request.user)

    def has_change_permission(self, request, obj=None):
        if not PayrollPolicy.can_edit_compensation(request.user):
            return False
        if obj is None:
            return True
        return PayrollPolicy.can_edit_compensation_for_user(request.user, obj.user)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        visible_users = User.objects.filter(is_active=True).exclude(role__name=Role.Name.INTERN).exclude(id=request.user.id)
        if not PayrollPolicy.can_manage_payroll(request.user):
            visible_users = visible_users.filter(
                department_id=getattr(request.user, "department_id", None),
                role__name=Role.Name.EMPLOYEE,
            )

        for user in visible_users:
            PayrollCompensation.objects.get_or_create(
                user=user,
                defaults={
                    "pay_type": PayrollCompensation.PayType.HOURLY,
                    "hourly_rate": getattr(user, "current_hourly_rate", 0),
                    "minute_rate": 0,
                    "fixed_salary": 0,
                },
            )

        qs = super().get_queryset(request).select_related("user", "user__role")
        qs = qs.filter(user__in=visible_users)
        if PayrollPolicy.can_manage_payroll(request.user):
            return qs
        return qs.filter(
            user__department_id=getattr(request.user, "department_id", None),
            user__role__name=Role.Name.EMPLOYEE,
        )
