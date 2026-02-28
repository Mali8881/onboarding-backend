from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ProcessCreateAPIView,
    ProcessDetailAPIView,
    ProcessListAPIView,
    ProcessTemplateAdminViewSet,
    StepCompleteAPIView,
    StepTemplateAdminViewSet,
)


router = DefaultRouter()
router.register(r"admin/templates", ProcessTemplateAdminViewSet, basename="bpm-admin-templates")
router.register(r"admin/step-templates", StepTemplateAdminViewSet, basename="bpm-admin-step-templates")


urlpatterns = [
    path("", ProcessListAPIView.as_view(), name="bpm-list"),
    path("instances/", ProcessCreateAPIView.as_view(), name="bpm-instance-create"),
    path("<int:pk>/", ProcessDetailAPIView.as_view(), name="bpm-detail"),
    path("steps/<int:step_id>/complete/", StepCompleteAPIView.as_view(), name="bpm-step-complete"),
    path("", include(router.urls)),
]
