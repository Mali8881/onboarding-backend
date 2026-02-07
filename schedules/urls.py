from django.urls import path
from .views import (
    WorkScheduleListView,
    WorkScheduleDetailView,
    WorkScheduleUsersView,
    AssignWorkScheduleView,
)

urlpatterns = [
    path("admin/schedules/", WorkScheduleListView.as_view()),
    path("admin/schedules/<uuid:id>/", WorkScheduleDetailView.as_view()),
    path("admin/schedules/<uuid:id>/users/", WorkScheduleUsersView.as_view()),
    path("admin/schedules/assign/", AssignWorkScheduleView.as_view()),
]
