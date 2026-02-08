from django.urls import path

from onboarding_core.urls import router
from .views import SubmitOnboardingReportView, AdminOnboardingReportViewSet

urlpatterns = [
    path("submit/", SubmitOnboardingReportView.as_view()),
]
router.register(
    r"admin/onboarding/reports",
    AdminOnboardingReportViewSet,
    basename="admin-onboarding-reports",
)