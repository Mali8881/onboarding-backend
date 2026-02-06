from django.urls import path
from .views import MyScheduleAPIView

urlpatterns = [
    path("my-schedule/", MyScheduleAPIView.as_view()),
]
