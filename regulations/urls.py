from django.urls import path
from .views import (
    FirstDayMandatoryRegulationsAPIView,
    RegulationAcknowledgeAPIView,
    RegulationAdminDetailAPIView,
    RegulationAdminListCreateAPIView,
    RegulationDetailAPIView,
    RegulationListAPIView,
)

urlpatterns = [
    path("", RegulationListAPIView.as_view(), name="regulations-list"),
    path("first-day/mandatory/", FirstDayMandatoryRegulationsAPIView.as_view(), name="regulations-first-day-mandatory"),
    path("<uuid:id>/acknowledge/", RegulationAcknowledgeAPIView.as_view(), name="regulations-acknowledge"),
    path("<uuid:id>/", RegulationDetailAPIView.as_view(), name="regulations-detail"),
    path("admin/", RegulationAdminListCreateAPIView.as_view(), name="regulations-admin-list-create"),
    path(
        "admin/<uuid:id>/",
        RegulationAdminDetailAPIView.as_view(),
        name="regulations-admin-detail",
    ),
]
