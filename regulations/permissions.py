from rest_framework.permissions import BasePermission

from accounts.access_policy import AccessPolicy


class IsAdminLike(BasePermission):
    """Allow only Admin or SuperAdmin roles."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return AccessPolicy.is_admin(user) or AccessPolicy.is_super_admin(user)

