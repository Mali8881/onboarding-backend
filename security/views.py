from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from common.permissions import IsSuperAdmin
from .models import SystemLog
from .serializers import SystemLogSerializer


class SystemLogViewSet(ModelViewSet):
    """
    Просмотр системных логов.
    Доступ ТОЛЬКО для superadmin.
    """

    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = SystemLogSerializer
    http_method_names = ["get"]  # только чтение

    def get_queryset(self):
        qs = SystemLog.objects.all().order_by("-created_at")

        # фильтр по уровню (INFO / WARNING / ERROR)
        level = self.request.query_params.get("level")
        if level:
            qs = qs.filter(level=level)

        # фильтр по типу действия
        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        # фильтр по пользователю
        actor_id = self.request.query_params.get("actor_id")
        if actor_id:
            qs = qs.filter(actor_id=actor_id)

        # фильтр по дате (from / to)
        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        return qs
