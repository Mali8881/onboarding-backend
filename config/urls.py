from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # AUTH
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # API v1
    path("api/v1/accounts/", include("accounts.urls")),

    path("api/v1/onboarding/", include("onboarding_core.urls")),
    path("api/v1/reports/", include("reports.urls")),
    path("api/v1/security/", include("security.urls")),
    path("api/v1/regulations/", include("regulations.urls")),
    path("api/v1/common/", include("common.urls")),
    path("api/v1/content/", include("content.urls")),
    path("api/v1/attendance/", include("apps.attendance.urls")),
    path("api/", include("work_schedule.urls")),
]
