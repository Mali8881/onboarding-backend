from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import HasPermission

from .models import SystemLog
from .serializers import SystemLogSerializer


class SystemLogViewSet(ModelViewSet):
    """
    Deprecated legacy read-model for system logs.
    New audit writes must go through apps.audit.log_event(...).
    This endpoint is read-only and kept for backward compatibility.
    """

    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "logs_read"
    serializer_class = SystemLogSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        qs = SystemLog.objects.all().order_by("-created_at")

        level = self.request.query_params.get("level")
        if level:
            qs = qs.filter(level=level)

        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        actor_id = self.request.query_params.get("actor_id")
        if actor_id:
            qs = qs.filter(actor_id=actor_id)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        return qs
