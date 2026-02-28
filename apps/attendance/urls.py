from django.urls import path

from .views import (
    AttendanceOverviewAPIView,
    AttendanceCalendarAPIView,
    AttendanceMarkAPIView,
    AttendanceDailyCheckInAPIView,
    AttendanceMyAPIView,
    AttendanceTeamAPIView,
    OfficeNetworkAdminAPIView,
    OfficeNetworkAdminDetailAPIView,
    WorkCalendarDayAdminAPIView,
    WorkCalendarGenerateAPIView,
)


urlpatterns = [
    path("", AttendanceOverviewAPIView.as_view(), name="attendance-overview"),
    path("calendar/", AttendanceCalendarAPIView.as_view(), name="attendance-calendar"),
    path("mark/", AttendanceMarkAPIView.as_view(), name="attendance-mark"),
    path("check-in/", AttendanceDailyCheckInAPIView.as_view(), name="attendance-check-in"),
    path("my/", AttendanceMyAPIView.as_view(), name="attendance-my"),
    path("team/", AttendanceTeamAPIView.as_view(), name="attendance-team"),
    path("admin/office-networks/", OfficeNetworkAdminAPIView.as_view(), name="attendance-office-networks"),
    path("admin/office-networks/<int:network_id>/", OfficeNetworkAdminDetailAPIView.as_view(), name="attendance-office-network-detail"),
    path("work-calendar/", WorkCalendarDayAdminAPIView.as_view(), name="attendance-work-calendar-admin"),
    path("work-calendar/generate/", WorkCalendarGenerateAPIView.as_view(), name="attendance-work-calendar-generate"),
]
