from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SubmitOnboardingReportView,
    AdminOnboardingReportViewSet,
    OnboardingReportLogViewSet,
    ReportNotificationViewSet,
)

router = DefaultRouter()
router.register(
    r"admin/onboarding/reports",
    AdminOnboardingReportViewSet,
    basename="admin-onboarding-reports",
)
router.register(
    r"admin/onboarding/report-logs",
    OnboardingReportLogViewSet,
    basename="admin-onboarding-report-logs",
)
router.register(
    r"notifications",
    ReportNotificationViewSet,
    basename="report-notifications",
)

urlpatterns = [
    path("submit/", SubmitOnboardingReportView.as_view(), name="submit-report"),
    path("", include(router.urls)),
]
