from django.contrib import admin
from django.contrib import messages

from .access_policy import AccessPolicy
from .models import (
    AuditLog,
    Department,
    LoginHistory,
    Permission,
    Position,
    Role,
    User,
)


def is_super_admin(user):
    return AccessPolicy.is_super_admin(user)


def is_admin(user):
    return AccessPolicy.is_admin(user)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "role", "manager", "is_blocked")
    list_filter = ("role", "is_blocked", "department")

    def has_module_permission(self, request):
        return AccessPolicy.can_access_admin_panel(request.user)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if not request.user.is_authenticated:
            return qs.none()

        if is_admin(request.user):
            return qs.filter(role__name__in=[Role.Name.INTERN, Role.Name.EMPLOYEE])

        return qs

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False

        if obj and is_admin(request.user):
            return AccessPolicy.can_manage_user(request.user, obj)

        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False

        if obj and is_admin(request.user):
            return False

        return super().has_delete_permission(request, obj)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "level")

    def has_module_permission(self, request):
        return is_super_admin(request.user)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "module")
    search_fields = ("codename", "module")

    def has_module_permission(self, request):
        return is_super_admin(request.user)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return AccessPolicy.has_permission(request.user, "logs_read")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active")
    list_filter = ("is_active", "parent")
    search_fields = ("name",)

    def has_module_permission(self, request):
        return request.user.is_authenticated

    def delete_model(self, request, obj):
        if obj.user_set.exists():
            self.message_user(
                request,
                "Нельзя удалить отдел: к нему привязаны пользователи.",
                level=messages.ERROR,
            )
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        blocked = queryset.filter(user__isnull=False).distinct()
        if blocked.exists():
            self.message_user(
                request,
                "Некоторые отделы не удалены: к ним привязаны пользователи.",
                level=messages.ERROR,
            )
            queryset = queryset.exclude(pk__in=blocked.values_list("pk", flat=True))
        super().delete_queryset(request, queryset)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_authenticated


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return is_super_admin(request.user)
