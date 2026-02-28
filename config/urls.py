from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .admin_views import (
    attendance_checkin_page,
    company_list_page,
    company_structure_page,
    content_dashboard,
    onboarding_dashboard,
    office_networks_page,
    profile_page,
    work_schedule_board_page,
)
from .health import health_check
from .spa_views import spa_asset, spa_index, spa_portal, spa_vite_icon

admin.site.site_header = "HRM Администрирование"
admin.site.site_title = "Админ-панель HRM"
admin.site.index_title = "Управление системой"


def public_schema_json_view(request):
    schema = SchemaGenerator().get_schema(request=None, public=True)
    return JsonResponse(schema, safe=False)


urlpatterns = [
    path("health/", health_check, name="health"),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("admin/onboarding/", onboarding_dashboard, name="admin-onboarding-dashboard"),
    path("admin/content/", content_dashboard, name="admin-content-dashboard"),
    path("admin/company/structure/", company_structure_page, name="admin-company-structure-page"),
    path("admin/company/list/", company_list_page, name="admin-company-list-page"),
    path("admin/attendance/check-in/", attendance_checkin_page, name="admin-attendance-checkin-page"),
    path("admin/attendance/office-networks/", office_networks_page, name="admin-office-networks-page"),
    path("admin/work-schedule-board/", work_schedule_board_page, name="admin-work-schedule-board"),
    path("admin/profile/", profile_page, name="admin-profile-page"),
    path("admin/login/portal/", spa_portal, name="admin-login-portal"),
    path("admin/", admin.site.urls),
    path("api/schema/", public_schema_json_view, name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            authentication_classes=[],
            permission_classes=[AllowAny],
        ),
        name="swagger-ui",
    ),
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
    path("api/v1/kb/", include("apps.kb.urls")),
    path("api/v1/metrics/", include("apps.metrics.urls")),
    path("api/v1/bpm/", include("apps.bpm.urls")),
    path("api/", include("work_schedule.urls")),
    path("assets/<path:asset_path>", spa_asset, name="spa-asset"),
    path("vite.svg", spa_vite_icon, name="spa-vite-icon"),
    path("", spa_index, name="spa-index"),
    re_path(
        r"^(?!admin/|api/|ckeditor5/|media/|static/|assets/|vite\.svg$).*$",
        spa_portal,
        name="spa-catch-all",
    ),
]
