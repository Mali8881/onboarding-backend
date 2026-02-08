from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from common.models import Notification

class NotificationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="""
Возвращает список уведомлений текущего пользователя.

Ответ содержит:
— количество непрочитанных уведомлений;
— список последних уведомлений (максимум 10).

Доступ: любой авторизованный пользователь.
""",
        responses={
            200: OpenApiResponse(
                description="Список уведомлений пользователя",
                response={
                    "type": "object",
                    "properties": {
                        "unread_count": {
                            "type": "integer",
                            "description": "Количество непрочитанных уведомлений"
                        },
                        "items": {
                            "type": "array",
                            "description": "Список последних уведомлений",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "ID уведомления"
                                    },
                                    "title": {
                                        "type": "string",
                                        "description": "Заголовок уведомления"
                                    },
                                    "is_read": {
                                        "type": "boolean",
                                        "description": "Прочитано ли уведомление"
                                    }
                                }
                            }
                        }
                    }
                }
            ),
            401: OpenApiResponse(description="Пользователь не авторизован")
        }
    )
    def get(self, request, pk=None):
        qs = Notification.objects.filter(
            user=request.user
        ).order_by("-created_at")

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
