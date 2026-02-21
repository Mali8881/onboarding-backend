from django.urls import path
from .views import (
    ProductionCalendarDayAdminAPIView,
    ProductionCalendarMonthGenerateAPIView,
    WorkScheduleListAPIView,
    WorkScheduleAdminListCreateAPIView,
    WorkScheduleAdminDetailAPIView,
    WorkScheduleRequestListAPIView,
    WorkScheduleRequestDecisionAPIView,
    WorkScheduleTemplateUsersAPIView,
    MyScheduleAPIView,
    ScheduleOptionsAPIView,
    CalendarView,
    ChooseScheduleAPIView,
    CalendarMonthAPIView,
)

urlpatterns = [
    # New v1 endpoints
    path("v1/work-schedules/", WorkScheduleListAPIView.as_view()),
    path("v1/work-schedules/my/", MyScheduleAPIView.as_view()),
    path("v1/work-schedules/select/", ChooseScheduleAPIView.as_view()),
    path("v1/work-schedules/calendar/", CalendarView.as_view()),
    path("v1/work-schedules/admin/templates/", WorkScheduleAdminListCreateAPIView.as_view()),
    path("v1/work-schedules/admin/templates/<int:schedule_id>/", WorkScheduleAdminDetailAPIView.as_view()),
    path("v1/work-schedules/admin/templates/<int:schedule_id>/users/", WorkScheduleTemplateUsersAPIView.as_view()),
    path("v1/work-schedules/admin/requests/", WorkScheduleRequestListAPIView.as_view()),
    path("v1/work-schedules/admin/requests/<int:request_id>/decision/", WorkScheduleRequestDecisionAPIView.as_view()),
    path("v1/work-schedules/admin/calendar/day/", ProductionCalendarDayAdminAPIView.as_view()),
    path("v1/work-schedules/admin/calendar/generate/", ProductionCalendarMonthGenerateAPIView.as_view()),

    # Legacy compatibility
    path("my-schedule/", MyScheduleAPIView.as_view()),
    path("schedules/", ScheduleOptionsAPIView.as_view()),
    path("calendar/", CalendarView.as_view(), name="calendar"),
    path("calendar-month/", CalendarMonthAPIView.as_view()),
    path("choose-schedule/", ChooseScheduleAPIView.as_view()),
]
