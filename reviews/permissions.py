from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsAdminOrSuperAdmin(permissions.BasePermission):
    """Разрешает доступ только администраторам и суперадминистраторам"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.role in [User.Role.ADMIN, User.Role.SUPER_ADMIN]

    def has_object_permission(self, request, view, obj):
        # Для большинства операций достаточно проверки has_permission
        return self.has_permission(request, view)