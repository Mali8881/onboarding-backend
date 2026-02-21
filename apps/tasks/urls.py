from django.urls import path

from .views import (
    TaskCreateAPIView,
    TaskDetailAPIView,
    TaskMoveAPIView,
    TaskMyAPIView,
    TaskTeamAPIView,
)


urlpatterns = [
    path("my/", TaskMyAPIView.as_view(), name="tasks-my"),
    path("team/", TaskTeamAPIView.as_view(), name="tasks-team"),
    path("create/", TaskCreateAPIView.as_view(), name="tasks-create"),
    path("<int:pk>/", TaskDetailAPIView.as_view(), name="tasks-detail"),
    path("<int:pk>/move/", TaskMoveAPIView.as_view(), name="tasks-move"),
]

