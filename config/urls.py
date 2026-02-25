from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .admin_views import (
    attendance_checkin_page,
    content_dashboard,
    onboarding_dashboard,
    work_schedule_board_page,
)
from .spa_views import spa_asset, spa_index, spa_vite_icon

admin.site.site_header = "HRM Администрирование"
admin.site.site_title = "Админ-панель HRM"
admin.site.index_title = "Управление системой"

urlpatterns = [
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("admin/onboarding/", onboarding_dashboard, name="admin-onboarding-dashboard"),
    path("admin/content/", content_dashboard, name="admin-content-dashboard"),
    path("admin/attendance/check-in/", attendance_checkin_page, name="admin-attendance-checkin-page"),
    path("admin/", admin.site.urls),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("api/v1/accounts/", include("accounts.urls")),
    path("api/v1/onboarding/", include("onboarding_core.urls")),
    path("api/v1/reports/", include("reports.urls")),
    path("api/v1/security/", include("security.urls")),
    path("api/v1/regulations/", include("regulations.urls")),
    path("api/v1/common/", include("common.urls")),
    path("api/v1/content/", include("content.urls")),
    path("api/v1/attendance/", include("apps.attendance.urls")),
    path("api/v1/tasks/", include("apps.tasks.urls")),
    path("api/v1/payroll/", include("apps.payroll.urls")),
    path("api/", include("work_schedule.urls")),
    path("assets/<path:asset_path>", spa_asset, name="spa-asset"),
    path("vite.svg", spa_vite_icon, name="spa-vite-icon"),
    path("", spa_index, name="spa-index"),
    re_path(r"^(?!admin/|api/|ckeditor5/|media/|static/).*$", spa_index, name="spa-catch-all"),
]
