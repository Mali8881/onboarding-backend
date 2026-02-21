from django.urls import path
from .views import (
    AdminApproveInternOnboardingAPIView,
    AdminInternOnboardingRequestListAPIView,
    FirstDayMandatoryRegulationsAPIView,
    InternOnboardingOverviewAPIView,
    MarkRegulationReadAPIView,
    RegulationAcknowledgeAPIView,
    RegulationAdminDetailAPIView,
    RegulationAdminListCreateAPIView,
    RegulationDetailAPIView,
    RegulationFeedbackCreateAPIView,
    RegulationListAPIView,
    StartInternOnboardingAPIView,
    SubmitInternOnboardingAPIView,
)

urlpatterns = [
    path("", RegulationListAPIView.as_view(), name="regulations-list"),
    path("intern/overview/", InternOnboardingOverviewAPIView.as_view(), name="intern-onboarding-overview"),
    path("intern/start/", StartInternOnboardingAPIView.as_view(), name="intern-onboarding-start"),
    path("intern/submit/", SubmitInternOnboardingAPIView.as_view(), name="intern-onboarding-submit"),
    path("<uuid:regulation_id>/read/", MarkRegulationReadAPIView.as_view(), name="regulation-read"),
    path("<uuid:regulation_id>/feedback/", RegulationFeedbackCreateAPIView.as_view(), name="regulation-feedback"),
    path("first-day/mandatory/", FirstDayMandatoryRegulationsAPIView.as_view(), name="regulations-first-day-mandatory"),
    path("<uuid:id>/acknowledge/", RegulationAcknowledgeAPIView.as_view(), name="regulations-acknowledge"),
    path("<uuid:id>/", RegulationDetailAPIView.as_view(), name="regulations-detail"),
    path("admin/", RegulationAdminListCreateAPIView.as_view(), name="regulations-admin-list-create"),
    path("admin/intern-requests/", AdminInternOnboardingRequestListAPIView.as_view(), name="admin-intern-requests"),
    path("admin/intern-requests/<int:request_id>/approve/", AdminApproveInternOnboardingAPIView.as_view(), name="admin-intern-requests-approve"),
    path(
        "admin/<uuid:id>/",
        RegulationAdminDetailAPIView.as_view(),
        name="regulations-admin-detail",
    ),
]
