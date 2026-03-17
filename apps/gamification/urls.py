from django.urls import path

from .views import MyGamificationAPIView


urlpatterns = [
    path("my/", MyGamificationAPIView.as_view(), name="gamification-my"),
]
