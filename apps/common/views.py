from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import Notification
from apps.common.serializers import NotificationSerializer
from apps.common.audit import CommonAuditService


class NotificationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _to_bool(value):
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return None

    @staticmethod
    def _to_int(value, default, min_value, max_value):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        if parsed < min_value:
            return min_value
        if parsed > max_value:
            return max_value
        return parsed

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        total_qs = qs

        notification_type = request.query_params.get("type")
        if notification_type:
            qs = qs.filter(type=notification_type)
            total_qs = total_qs.filter(type=notification_type)

        unread = self._to_bool(request.query_params.get("unread"))
        if unread is not None:
            qs = qs.filter(is_read=not not unread)
            total_qs = total_qs.filter(is_read=not not unread)

        offset = self._to_int(request.query_params.get("offset"), default=0, min_value=0, max_value=100000)
        limit = self._to_int(request.query_params.get("limit"), default=20, min_value=1, max_value=100)
        items = qs[offset: offset + limit]

        return Response({
            "unread_count": Notification.objects.filter(user=request.user, is_read=False).count(),
            "total_count": total_qs.count(),
            "items": NotificationSerializer(
                items, many=True
            ).data,
        })


class MarkNotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        notification = Notification.objects.filter(
            pk=pk,
            user=request.user
        ).first()

        if not notification:
            return Response({"error": "Not found"}, status=404)

        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
            CommonAuditService.log_notification_marked_read(request, notification)

        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"status": "marked as read", "unread_count": unread_count})


class MarkAllNotificationsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        updated_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        CommonAuditService.log_notifications_marked_read_all(request, updated_count)

        return Response({"status": "all marked as read", "updated_count": int(updated_count), "unread_count": 0})
