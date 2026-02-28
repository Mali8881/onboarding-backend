from django.urls import path

from .views import MetricsMyAPIView, MetricsTeamAPIView


urlpatterns = [
    path("", MetricsMyAPIView.as_view(), name="metrics-my"),
    path("team/", MetricsTeamAPIView.as_view(), name="metrics-team"),
]
