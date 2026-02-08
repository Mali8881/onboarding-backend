from django.urls import path
from rest_framework.routers import DefaultRouter


from .views import (
    OnboardingDayListView,
    OnboardingDayDetailView,
    CompleteOnboardingDayView,
    OnboardingOverviewView,
    AdminOnboardingDayViewSet,
    AdminOnboardingMaterialViewSet,
    AdminOnboardingProgressViewSet,
    SubmitOnboardingReportView, AdminOnboardingReportViewSet,

)

router = DefaultRouter()
router.register(
    r"admin/onboarding/days",
    AdminOnboardingDayViewSet,
    basename="admin-onboarding-days",
)
router.register(
    r"admin/onboarding/materials",
    AdminOnboardingMaterialViewSet,
    basename="admin-onboarding-materials",
)
router.register(
    r"admin/onboarding/progress",
    AdminOnboardingProgressViewSet,
    basename="admin-onboarding-progress",
)
router.register(
    r"admin/onboarding/reports",
    AdminOnboardingReportViewSet,
    basename="admin-onboarding-reports",
)


urlpatterns = [
    path("days/", OnboardingDayListView.as_view()),
    path("days/<uuid:id>/", OnboardingDayDetailView.as_view()),
    path("days/<uuid:id>/complete/", CompleteOnboardingDayView.as_view()),
    path("overview/", OnboardingOverviewView.as_view()),
    path("reports/submit/", SubmitOnboardingReportView.as_view()),
]


urlpatterns += router.urls
