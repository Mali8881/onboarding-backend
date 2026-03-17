from django.urls import path

from .views import (
    TaskAssigneesAPIView,
    TaskCreateAPIView,
    TaskDetailAPIView,
    TaskMoveLogAPIView,
    TaskMoveAPIView,
    TaskMyAPIView,
    TaskTeamAPIView,
)


urlpatterns = [
    path("my/", TaskMyAPIView.as_view(), name="tasks-my"),
    path("team/", TaskTeamAPIView.as_view(), name="tasks-team"),
    path("assignees/", TaskAssigneesAPIView.as_view(), name="tasks-assignees"),
    path("create/", TaskCreateAPIView.as_view(), name="tasks-create"),
    path("moves/", TaskMoveLogAPIView.as_view(), name="tasks-moves"),
    path("<int:pk>/", TaskDetailAPIView.as_view(), name="tasks-detail"),
    path("<int:pk>/move/", TaskMoveAPIView.as_view(), name="tasks-move"),
]

