from django.urls import path
from .views import MyScheduleAPIView, CalendarView

urlpatterns = [
    path("my-schedule/", MyScheduleAPIView.as_view()),
    path("calendar/", CalendarView.as_view(), name="calendar"),
]
