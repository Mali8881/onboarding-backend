from rest_framework.permissions import BasePermission


def is_in_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()

from rest_framework.permissions import BasePermission


def is_in_group(user, group_name: str) -> bool:
    """
    Проверка принадлежности пользователя к группе.
    Используется как основа RBAC.
    """
    return (
        user.is_authenticated
        and user.groups.filter(name=group_name).exists()
    )


class IsIntern(BasePermission):
    """
    Доступ только для стажёров
    """
    def has_permission(self, request, view):
        return is_in_group(request.user, "INTERN")


class IsAdmin(BasePermission):
    """
    Доступ только для администраторов
    """
    def has_permission(self, request, view):
        return is_in_group(request.user, "ADMIN")


class IsSuperAdmin(BasePermission):
    """
    Доступ только для суперадминистраторов
    """
    def has_permission(self, request, view):
        return is_in_group(request.user, "SUPER_ADMIN")


class IsAdminOrSuperAdmin(BasePermission):
    """
    Доступ для администратора или суперадминистратора
    """
    def has_permission(self, request, view):
        return (
            is_in_group(request.user, "ADMIN")
            or is_in_group(request.user, "SUPER_ADMIN")
        )



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
