from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    MeView,
    AdminUserViewSet,
)

router = DefaultRouter()
router.register(
    r"admin/users",
    AdminUserViewSet,
    basename="admin-users",
)

urlpatterns = [
    # AUTH
    path("auth/login/", LoginView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),

    # USER
    path("users/me/", MeView.as_view()),

    # ADMIN (router)
    path("", include(router.urls)),
]
