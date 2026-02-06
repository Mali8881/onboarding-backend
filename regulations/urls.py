from django.urls import path
from .views import RegulationListAPIView

urlpatterns = [
    path("regulations/", RegulationListAPIView.as_view(), name="regulations-list"),
]
