from django.urls import path
from .views import MeAPIView, LogoutAPIView

urlpatterns = [
    path("me/", MeAPIView.as_view()),
    path("logout/", LogoutAPIView.as_view()),
]
