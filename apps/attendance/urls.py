from django.urls import path

from .views import (
    AttendanceOverviewAPIView,
    AttendanceCalendarAPIView,
    AttendanceMarkAPIView,
    AttendanceMyAPIView,
    AttendanceTeamAPIView,
    WorkCalendarDayAdminAPIView,
    WorkCalendarGenerateAPIView,
)


urlpatterns = [
    path("", AttendanceOverviewAPIView.as_view(), name="attendance-overview"),
    path("calendar/", AttendanceCalendarAPIView.as_view(), name="attendance-calendar"),
    path("mark/", AttendanceMarkAPIView.as_view(), name="attendance-mark"),
    path("my/", AttendanceMyAPIView.as_view(), name="attendance-my"),
    path("team/", AttendanceTeamAPIView.as_view(), name="attendance-team"),
    path("work-calendar/", WorkCalendarDayAdminAPIView.as_view(), name="attendance-work-calendar-admin"),
    path("work-calendar/generate/", WorkCalendarGenerateAPIView.as_view(), name="attendance-work-calendar-generate"),
]
