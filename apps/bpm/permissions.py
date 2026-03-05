from rest_framework.permissions import BasePermission

from accounts.access_policy import AccessPolicy


class CanManageBpmTemplates(BasePermission):
    """Only roles with bpm.manage_templates permission (Admin, Administrator, SuperAdmin)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and AccessPolicy.can_manage_bpm_templates(request.user)
        )
