from rest_framework.permissions import BasePermission

from accounts.access_policy import AccessPolicy


class IsAdminLike(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and AccessPolicy.is_admin_like(request.user))
