from django.urls import path

from .views import (
    AttendanceCalendarAPIView,
    AttendanceMarkAPIView,
    AttendanceMyAPIView,
    AttendanceTeamAPIView,
)


urlpatterns = [
    path("calendar/", AttendanceCalendarAPIView.as_view(), name="attendance-calendar"),
    path("mark/", AttendanceMarkAPIView.as_view(), name="attendance-mark"),
    path("my/", AttendanceMyAPIView.as_view(), name="attendance-my"),
    path("team/", AttendanceTeamAPIView.as_view(), name="attendance-team"),
]

