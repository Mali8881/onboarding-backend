from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    KBArticleAdminViewSet,
    KBArticleDetailAPIView,
    KBArticleListAPIView,
    KBCategoryAdminViewSet,
    KBReportAPIView,
)


router = DefaultRouter()
router.register(r"admin/articles", KBArticleAdminViewSet, basename="kb-admin-articles")
router.register(r"admin/categories", KBCategoryAdminViewSet, basename="kb-admin-categories")


urlpatterns = [
    path("", KBArticleListAPIView.as_view(), name="kb-list"),
    path("report/", KBReportAPIView.as_view(), name="kb-report"),
    path("<int:pk>/", KBArticleDetailAPIView.as_view(), name="kb-detail"),
    path("", include(router.urls)),
]
