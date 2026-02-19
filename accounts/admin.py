from django.contrib import admin
from .models import (
    User,
    Role,
    Permission,
    Department,
    Position,
    AuditLog,
    LoginHistory,
)


# ================= SAFE HELPERS =================

def is_super_admin(user):
    return (
        user.is_authenticated
        and hasattr(user, "role")
        and user.role
        and user.role.name == "SUPER_ADMIN"
    )


def is_admin(user):
    return (
        user.is_authenticated
        and hasattr(user, "role")
        and user.role
        and user.role.name == "ADMIN"
    )


# ================= USER =================

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "role", "is_blocked")
    list_filter = ("role", "is_blocked")

    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_staff

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if not request.user.is_authenticated:
            return qs.none()

        # ADMIN видит только стажёров
        if is_admin(request.user):
            return qs.filter(role__name="INTERN")

        return qs

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False

        if obj and is_admin(request.user):
            # ADMIN не может менять админов и супер-админов
            if obj.role.name != "INTERN":
                return False

        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False

        if obj and is_admin(request.user):
            return False  # ADMIN не удаляет пользователей

        return super().has_delete_permission(request, obj)


# ================= ROLE =================

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):

    def has_module_permission(self, request):
        return is_super_admin(request.user)


# ================= PERMISSION =================

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):

    def has_module_permission(self, request):
        return is_super_admin(request.user)


# ================= AUDIT LOG =================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.has_permission("logs_read")


# ================= OTHER MODELS =================

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):

    def has_module_permission(self, request):
        return request.user.is_authenticated


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):

    def has_module_permission(self, request):
        return request.user.is_authenticated


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):

    def has_module_permission(self, request):
        return is_super_admin(request.user)
