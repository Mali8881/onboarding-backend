from django.urls import path
from .views import (
    MyScheduleAPIView,
    CalendarView,
    ChooseScheduleAPIView,
    CalendarMonthAPIView,
)

urlpatterns = [
    path("my-schedule/", MyScheduleAPIView.as_view()),
    path("calendar/", CalendarView.as_view(), name="calendar"),
    path("calendar-month/", CalendarMonthAPIView.as_view()),
    path("choose-schedule/", ChooseScheduleAPIView.as_view()),
]
