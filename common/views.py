from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import Notification


class NotificationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        return Response({
            "unread_count": qs.filter(is_read=False).count(),
            "items": [
                {
                    "id": n.id,
                    "title": n.title,
                    "is_read": n.is_read,
                }
                for n in qs.order_by("-created_at")[:10]
            ]
        })
