
from django.urls import path
from .views import (
    MyProfileAPIView,
    DepartmentListAPIView,
    PositionListAPIView,
)

urlpatterns = [
    path("me/profile/", MyProfileAPIView.as_view()),
    path("departments/", DepartmentListAPIView.as_view()),
    path("positions/", PositionListAPIView.as_view()),
]
