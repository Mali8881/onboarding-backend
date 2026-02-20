from django.urls import path
from .views import (
    MarkAllNotificationsReadAPIView,
    MarkNotificationReadAPIView,
    NotificationsAPIView,
)



urlpatterns = [
    path("notifications/", NotificationsAPIView.as_view()),
    path("notifications/<int:pk>/read/", MarkNotificationReadAPIView.as_view()),
    path("notifications/read-all/", MarkAllNotificationsReadAPIView.as_view()),
]
