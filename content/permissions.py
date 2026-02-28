from rest_framework.permissions import BasePermission

from accounts.access_policy import AccessPolicy


class IsAdminOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return AccessPolicy.is_admin_like(user)
