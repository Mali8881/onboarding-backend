from rest_framework.permissions import BasePermission

from accounts.access_policy import AccessPolicy


class CanManageKb(BasePermission):
    """Only roles with kb.delete permission (Admin, Administrator, SuperAdmin)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and AccessPolicy.can_manage_kb(request.user)
        )
