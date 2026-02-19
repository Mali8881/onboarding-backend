from django.urls import path
from .views import *
from .views import MyProfileAPIView



urlpatterns = [
    path("login/", LoginView.as_view()),
    path("me/profile/", MyProfileAPIView.as_view(), name="my-profile"),
    path("positions/", PositionListAPIView.as_view()),
]

