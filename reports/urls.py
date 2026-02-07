from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    # USER
    MyReportListView,
    MyReportDetailView,
    MyReportCreateView,
    SubmitReportView,
    ReportHistoryView,
    MyReportNotificationsView,
    MarkNotificationReadView,
    MyUnreadNotificationsCountView,

    # ADMIN
    AdminReportViewSet,
    AdminReportStatusView,
    OnboardingStatsView,
)

router = DefaultRouter()
router.register(
    r"admin/reports",
    AdminReportViewSet,
    basename="admin-reports",
)

urlpatterns = [
    # ======================
    # USER
    # ======================
    path("reports/", MyReportListView.as_view(), name="my-reports"),
    path("reports/create/", MyReportCreateView.as_view(), name="report-create"),
    path("reports/<uuid:id>/", MyReportDetailView.as_view(), name="report-detail"),
    path("reports/<uuid:id>/submit/", SubmitReportView.as_view(), name="report-submit"),
    path("reports/<uuid:id>/history/", ReportHistoryView.as_view(), name="report-history"),

    # 🔔 notifications
    path(
        "reports/notifications/",
        MyReportNotificationsView.as_view(),
        name="report-notifications",
    ),
    path(
        "reports/notifications/<uuid:id>/read/",
        MarkNotificationReadView.as_view(),
        name="notification-read",
    ),
    path(
        "reports/notifications/unread-count/",
        MyUnreadNotificationsCountView.as_view(),
        name="notifications-unread-count",
    ),

    # ======================
    # ADMIN
    # ======================
    path(
        "admin/reports/<uuid:id>/status/",
        AdminReportStatusView.as_view(),
        name="admin-report-status",
    ),
    path(
        "admin/reports/stats/",
        OnboardingStatsView.as_view(),
        name="admin-report-stats",
    ),
]

urlpatterns += router.urls
