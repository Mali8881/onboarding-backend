from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.audit import CommonAuditService
from common.models import Notification
from common.serializers import NotificationSerializer


def _active_notifications_queryset(user):
    now = timezone.now()
    return Notification.objects.filter(user=user).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))


class NotificationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _active_notifications_queryset(request.user)

        notification_type = request.query_params.get("type")
        if notification_type:
            qs = qs.filter(type=notification_type)

        return Response(
            {
                "unread_count": qs.filter(is_read=False).count(),
                "items": NotificationSerializer(qs[:20], many=True).data,
            }
        )


class MarkNotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        notification = Notification.objects.filter(
            pk=pk,
            user=request.user,
        ).first()

        if not notification:
            return Response({"error": "Not found"}, status=404)

        notification.is_read = True
        notification.save()
        CommonAuditService.log_notification_marked_read(request, notification)

        return Response({"status": "marked as read"})


class MarkAllNotificationsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        updated_count = _active_notifications_queryset(request.user).filter(is_read=False).update(is_read=True)
        CommonAuditService.log_notifications_marked_read_all(request, updated_count)

        return Response({"status": "all marked as read"})
