from rest_framework.permissions import BasePermission


def is_in_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_in_group(request.user, "SUPER_ADMIN") or request.user.is_superuser


class HasPermissionCodename(BasePermission):
    """
    Проверяет наличие конкретного permission codename у пользователя.
    Использование:
      permission_classes = [HasPermissionCodename]
      required_permission = "reports_review"
    """
    required_permission = None

    def has_permission(self, request, view):
        code = getattr(view, "required_permission", None) or self.required_permission
        if not code:
            return False
        return request.user.is_authenticated and request.user.has_perm(f"accounts.{code}")
