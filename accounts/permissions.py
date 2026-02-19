from rest_framework.permissions import BasePermission


class HasPermission(BasePermission):
    """
    Универсальный permission-класс.
    В View нужно указать:
        permission_classes = [HasPermission]
        required_permission = "permission_code"
    """

    def has_permission(self, request, view):
        # Пользователь должен быть авторизован
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Проверяем, что View указал required_permission
        required = getattr(view, "required_permission", None)
        if not required:
            return False

        # Проверяем наличие permission через модель User
        return user.has_permission(required)