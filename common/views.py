from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import Notification
from common.serializers import NotificationSerializer


class NotificationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        qs = Notification.objects.filter(user=request.user)

        notification_type = request.query_params.get("type")
        if notification_type:
            qs = qs.filter(type=notification_type)

        return Response({
            "unread_count": qs.filter(is_read=False).count(),
            "items": NotificationSerializer(
                qs[:20], many=True
            ).data
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

        notification.is_read = True
        notification.save()

        return Response({"status": "marked as read"})


class MarkAllNotificationsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return Response({"status": "all marked as read"})
